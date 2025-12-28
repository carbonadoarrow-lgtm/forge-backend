from __future__ import annotations
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# v2 core imports
from forge.autonomy.store.run_store_v2 import RunStoreV2
from forge.autonomy.events.event_bus_v2 import EventBusV2
from forge.autonomy.config.config_registry import ConfigRegistry
from forge.autonomy.config.kill_switch_v2 import KillSwitchRegistry
from forge.autonomy.audit.audit_log import AuditLog
from forge.autonomy.leases.lease_store import LeaseStore
from forge.autonomy.scheduler.scheduler_v2 import SchedulerV2, SchedulerCaps
from forge.autonomy.graph_tick_v2 import GraphTickV2
from forge.autonomy.worker_v2 import WorkerV2
from forge.autonomy.policy_loader_v2 import AutonomyPolicyLoaderV2
from forge.autonomy.artifact_writer_v2 import ArtifactWriterV2

# Import existing routers and config
from src.config import settings
from src.routers import forge_router, orunmila_router
from forge.autonomy.cockpit_api import router as cockpit_router
from forge.autonomy.api_v2 import router as autonomy_v2_router

# Import migration script
from scripts.db.apply_migrations import main as apply_migrations

import sqlite3
from contextlib import contextmanager

# --- Provenance imports ---
import os
import sys
import json
import platform
from pathlib import Path
from typing import Any, Dict, Optional
import asyncio

from forge.autonomy.worker_guard_v2 import can_start_worker, mark_started_once

@contextmanager
def get_db():
    """
    SQLite database connection factory.
    Returns a connection object.
    """
    conn = sqlite3.connect(settings.DATABASE_URL.replace("sqlite:///", ""))
    try:
        yield conn
    finally:
        conn.close()


# D.11: Standardized error envelopes and audit helpers
def _error(code: str, message: str, detail: Any = None, http_status: int = 400) -> dict:
    """
    Create a standardized error envelope.

    Returns: {"error": {"code": str, "message": str, "detail": any}}
    """
    error_obj = {"code": code, "message": message}
    if detail is not None:
        error_obj["detail"] = detail
    return {"error": error_obj}


def _audit(
    action: str,
    result: str,
    actor_id: Optional[str] = None,
    actor_role: Optional[str] = None,
    target_id: Optional[str] = None,
    payload: Optional[dict] = None,
    error: Optional[dict] = None
) -> None:
    """
    Write an audit log entry.

    Keeps payloads compact; does not store secrets.
    """
    import datetime

    try:
        # Use FORGE_DB_PATH if set, otherwise use settings.DATABASE_URL
        # This allows tests to override the database path
        db_path = os.environ.get("FORGE_DB_PATH")
        if db_path:
            conn = sqlite3.connect(db_path)
        else:
            db_url = settings.DATABASE_URL.replace("sqlite:///", "")
            conn = sqlite3.connect(db_url)

        try:
            cur = conn.cursor()

            # Sanitize payload - remove any fields that might contain secrets
            safe_payload = None
            if payload:
                safe_payload = {k: v for k, v in payload.items() if not any(
                    secret_key in k.lower() for secret_key in ['token', 'password', 'secret', 'key']
                )}

            cur.execute(
                """
                INSERT INTO audit_log (ts, actor_id, actor_role, action, target_id, result, payload_json, error_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
                    actor_id,
                    actor_role,
                    action,
                    target_id,
                    result,
                    json.dumps(safe_payload) if safe_payload else None,
                    json.dumps(error) if error else None
                )
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        # Don't fail the request if audit logging fails
        print(f"WARNING: Audit log write failed: {e}", file=sys.stderr)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(forge_router, prefix=settings.API_PREFIX)
    app.include_router(orunmila_router, prefix=settings.API_PREFIX)
    app.include_router(cockpit_router)
    app.include_router(autonomy_v2_router)

    async def _background_worker_loop():
        """
        Stabilization-only background loop.
        Uses existing app.state.WorkerV2 + SchedulerCaps, no new architecture.
        """
        worker = getattr(app.state, "worker_v2", None)
        caps_cls = getattr(app.state, "SchedulerCaps", None)
        if worker is None or caps_cls is None:
            return

        def _default_caps():
            return caps_cls(
                max_total_ticks_per_invocation=1,
                max_ticks_per_run_per_invocation=1,
                daily_tick_cap=10_000,
            )

        while True:
            try:
                caps = _default_caps()
                worker.tick_once(
                    env=getattr(settings, "AUTONOMY_V2_WORKER_ENV", "local"),
                    lane=getattr(settings, "AUTONOMY_V2_WORKER_LANE", "default"),
                    owner_id=f"bg:{os.getpid()}",
                    caps=caps,
                    lease_ttl_seconds=15,
                )
            except Exception:
                # Never crash the server because the worker tick failed.
                pass
            await asyncio.sleep(getattr(settings, "AUTONOMY_V2_WORKER_TICK_INTERVAL_SECONDS", 3))

    @app.on_event("startup")
    async def _maybe_start_background_worker():
        status = can_start_worker(
            enabled=getattr(settings, "AUTONOMY_V2_WORKER_ENABLED", False),
            configured_pid=getattr(settings, "AUTONOMY_V2_WORKER_PID", 0),
        )
        app.state.worker_guard_status = status

        if not status.enabled:
            return
        if not mark_started_once():
            return

        asyncio.create_task(_background_worker_loop())

    @app.on_event("startup")
    def _startup() -> None:
        # Run database migrations
        apply_migrations()
        
        # 1) DB handle (shared) — OK if it is a pool/engine; if it's a session, create per-request instead.
        # We'll use a connection factory
        
        # 2) Core registries
        config_registry = ConfigRegistry(get_db)
        kill_switch_registry = KillSwitchRegistry(config_registry)
        audit_log = AuditLog(get_db)

        # 3) Run store + events
        run_store_v2 = RunStoreV2(get_db)
        event_bus_v2 = EventBusV2(get_db)

        # 4) Scheduler + leases
        lease_store = LeaseStore(get_db)
        scheduler_v2 = SchedulerV2(get_db)

        # 5) Policy loader + artifact writer
        policy_loader = AutonomyPolicyLoaderV2(config_registry=config_registry)
        artifact_writer = ArtifactWriterV2(base_dir="artifacts")

        # 6) Graph tick + worker
        graph_tick_v2 = GraphTickV2(
            store=run_store_v2,
            bus=event_bus_v2,
            policy_loader=policy_loader,
            artifact_writer=artifact_writer,
        )
        worker_v2 = WorkerV2(
            scheduler=scheduler_v2,
            leases=lease_store,
            ticker=graph_tick_v2,
            bus=event_bus_v2,
            kill_switch=kill_switch_registry.get_active(),  # NOTE: if WorkerV2 expects registry, pass registry not object
        )

        # 7) Attach to app.state (singletons)
        app.state.get_db = get_db
        app.state.config_registry = config_registry
        app.state.kill_switch_registry = kill_switch_registry
        app.state.audit_log = audit_log
        app.state.run_store_v2 = run_store_v2
        app.state.event_bus_v2 = event_bus_v2
        app.state.lease_store = lease_store
        app.state.scheduler_v2 = scheduler_v2
        app.state.graph_tick_v2 = graph_tick_v2
        app.state.worker_v2 = worker_v2

        # Optional: expose SchedulerCaps class for cockpit_api to build caps objects
        app.state.SchedulerCaps = SchedulerCaps

    # --- Provenance helpers and /api/health endpoint ---

    def _module_file(modname: str) -> Optional[str]:
        try:
            m = __import__(modname, fromlist=["__file__"])
            return getattr(m, "__file__", None)
        except Exception:
            return None

    def _provenance_snapshot() -> Dict[str, Any]:
        # repo root heuristic: forge-backend directory
        here = Path(__file__).resolve()
        forge_backend_root = here.parents[2]  # .../forge-backend

        # key modules to fingerprint (safe if missing)
        mods = [
            "forge",
            "forge.autonomy",
            "forge.autonomy.graph_tick_v2",
            "forge.autonomy.worker_v2",
            "forge.autonomy.scheduler.scheduler_v2",
            "forge.autonomy.store.run_store_v2",
            "forge.autonomy.events.event_bus_v2",
        ]

        return {
            "build": {
                "sha": getattr(settings, "BUILD_SHA", "unknown"),
                "time_utc": getattr(settings, "BUILD_TIME_UTC", "unknown"),
            },
            "runtime": {
                "python": sys.version.split()[0],
                "platform": platform.platform(),
                "cwd": str(Path.cwd()),
                "repo_root_guess": str(forge_backend_root),
            },
            "imports": {m: _module_file(m) for m in mods},
            "env": {
                # keep this minimal; do not leak secrets
                "FORGE_DB_PATH": os.environ.get("FORGE_DB_PATH"),
                "DATABASE_URL": getattr(settings, "DATABASE_URL", None),
                "NEXT_PUBLIC_FORGE_BACKEND_URL": os.environ.get("NEXT_PUBLIC_FORGE_BACKEND_URL"),
            },
        }

    @app.get("/")
    async def root():
        return {
            "message": "Forge Backend v1 with Jobs + LETO-BLRM",
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "health": "/healthz"
        }

    @app.get("/health")
    @app.get("/healthz")
    async def health():
        return {
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "mode": settings.FORGE_BACKEND_MODE
        }

    @app.get("/api/health")
    async def api_health() -> dict:
        """
        Stabilization-only health check with provenance.
        This endpoint MUST help detect 'wrong repo imported' failures.
        """
        snap = _provenance_snapshot()
        # Basic sanity: ensure forge resolves inside forge-backend if possible
        forge_path = (snap.get("imports") or {}).get("forge") or ""
        snap["sanity"] = {
            "forge_import_ok": ("forge-backend" in (forge_path or "")) or (forge_path != ""),
            "forge_path": forge_path,
        }
        guard = getattr(app.state, "worker_guard_status", None)
        if guard is not None:
            snap["autonomy_v2_worker"] = {
                "enabled": guard.enabled,
                "reason": guard.reason,
                "pid": guard.pid,
                "configured_pid": guard.configured_pid,
                "tick_interval_seconds": getattr(settings, "AUTONOMY_V2_WORKER_TICK_INTERVAL_SECONDS", 3),
                "env": getattr(settings, "AUTONOMY_V2_WORKER_ENV", "local"),
                "lane": getattr(settings, "AUTONOMY_V2_WORKER_LANE", "default"),
            }
        return snap

    def _require_admin(request):
        # Be tolerant to header casing used by different clients / proxies.
        token = request.headers.get("X-Admin-Token") or request.headers.get("x-admin-token") or ""
        expected = getattr(settings, "ADMIN_TOKEN", "") or ""
        if not expected:
            raise HTTPException(status_code=503, detail="admin_token_not_configured")
        if token != expected:
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.get("/api/autonomy/v2/worker/status")
    def autonomy_v2_worker_status(request):
        _require_admin(request)
        # existing implementation below; keep it, but avoid ConfigRegistry.get crash
        cfg = app.state.config_registry
        kill = app.state.kill_switch_registry
        worker = app.state.worker_v2
        guard = getattr(app.state, "worker_guard_v2", None)

        # The endpoint should never 500 because a config blob is missing.
        # policy is optional for status display; None is valid.
        policy = cfg.get("policy_v2") if hasattr(cfg, "get") else None

        return {
            "ok": True,
            "guard": guard.status() if guard else None,
            "config": {
                "env": settings.AUTONOMY_V2_WORKER_ENV,
                "lane": settings.AUTONOMY_V2_WORKER_LANE,
                "enabled": bool(getattr(settings, "AUTONOMY_V2_WORKER_ENABLED", False)),
                "tick_interval_seconds": getattr(settings, "AUTONOMY_V2_WORKER_TICK_INTERVAL_SECONDS", None),
            },
            "policy": policy,
            "kill_switch": kill.snapshot() if hasattr(kill, "snapshot") else None,
            "worker": worker.status() if hasattr(worker, "status") else None,
        }

    @app.post("/api/autonomy/v2/worker/tick-once")
    def worker_tick_once(x_admin_token: str = Header(default="", alias="X-Admin-Token")) -> Dict[str, Any]:
        _require_admin(x_admin_token)

        worker = getattr(app.state, "worker_v2", None)
        caps_cls = getattr(app.state, "SchedulerCaps", None)
        if worker is None or caps_cls is None:
            raise HTTPException(status_code=503, detail="worker_v2_not_wired")

        caps = caps_cls(
            max_total_ticks_per_invocation=1,
            max_ticks_per_run_per_invocation=1,
            daily_tick_cap=10_000,
        )
        env = getattr(settings, "AUTONOMY_V2_WORKER_ENV", "local")
        lane = getattr(settings, "AUTONOMY_V2_WORKER_LANE", "default")
        owner = f"manual:{os.getpid()}"

        # This calls the same worker implementation used by background loop.
        worker.tick_once(env=env, lane=lane, owner_id=owner, caps=caps, lease_ttl_seconds=15)
        return {"ok": True, "env": env, "lane": lane, "owner_id": owner}

    return app
