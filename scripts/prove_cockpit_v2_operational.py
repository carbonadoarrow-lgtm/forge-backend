"""
Operational proof for Cockpit v2 in forge-backend (no UI required):

1) apply migrations
2) create v2 run with 1-step noop graph
3) tick worker until terminal or budget exhausted
4) verify:
   - runs_v2 row exists
   - run_state_v2 exists
   - events exist
"""

import os
import sqlite3
import sys
from pathlib import Path

# Ensure this repo's root is first on sys.path so local "forge" package wins
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from db.apply_migrations import main as apply_migs


def main() -> int:
    apply_migs()
    db_path = os.environ.get("FORGE_DB_PATH", "forge.db")

    # Import minimal v2 core from this repo
    from forge.autonomy.store.run_store_v2 import RunStoreV2
    from forge.autonomy.events.event_bus_v2 import EventBusV2
    from forge.autonomy.config.config_registry import ConfigRegistry
    from forge.autonomy.config.kill_switch_v2 import KillSwitchRegistry
    from forge.autonomy.leases.lease_store import LeaseStore
    from forge.autonomy.scheduler.scheduler_v2 import SchedulerV2, SchedulerCaps
    from forge.autonomy.graph_tick_v2 import GraphTickV2
    from forge.autonomy.worker_v2 import WorkerV2

    # SQLite session_factory
    def sf():
        return sqlite3.connect(db_path)

    store = RunStoreV2(sf)
    bus = EventBusV2(sf)
    cfg = ConfigRegistry(sf)
    kill = KillSwitchRegistry(cfg)
    leases = LeaseStore(sf)
    sched = SchedulerV2(sf)

    # Minimal policy/artifact stubs for proof (dry_run only)
    class _Policy:
        def dispatch_allowed(self, state, step):
            return True, ""

    class _Artifacts:
        pass

    ticker = GraphTickV2(store=store, bus=bus, policy_loader=_Policy(), artifact_writer=_Artifacts())
    worker = WorkerV2(scheduler=sched, leases=leases, ticker=ticker, bus=bus, kill_switch=kill)

    run_graph = {
        "schema_version": "v2",
        "entry_step": "noop",
        "steps": {
            "noop": {
                "id": "noop",
                "deps": [],
                "kind": "noop",
            }
        },
    }
    run_id = store.create_run_v2(
        env="local",
        lane="default",
        mode="dry_run",
        job_type="autobuilder",
        requested_by="proof",
        run_graph=run_graph,
        params={},
    )

    caps = SchedulerCaps(
        max_total_ticks_per_invocation=5,
        max_ticks_per_run_per_invocation=5,
        daily_tick_cap=100,
    )
    worker.tick_once(env="local", lane="default", owner_id="proof", caps=caps, lease_ttl_seconds=15)

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # Verify runs_v2 row
    cur.execute("SELECT status FROM runs_v2 WHERE run_id = ?", (run_id,))
    row = cur.fetchone()
    if not row:
        print("FAIL: runs_v2 missing row")
        return 1

    # Verify run_state_v2 row
    cur.execute("SELECT COUNT(1) FROM run_state_v2 WHERE run_id = ?", (run_id,))
    if cur.fetchone()[0] < 1:
        print("FAIL: run_state_v2 missing")
        return 1

    # Verify events
    cur.execute("SELECT COUNT(1) FROM run_events_v2 WHERE run_id = ?", (run_id,))
    n_evt = cur.fetchone()[0]
    if n_evt < 2:
        print("FAIL: expected events>=2")
        return 1

    print(f"OK: run_id={run_id} status={row[0]} events={n_evt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
