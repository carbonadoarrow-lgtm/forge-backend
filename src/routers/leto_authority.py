"""
LETO Authority API router for authority telemetry, shadow queue, and SSE streams.

Endpoints:
- GET /leto/authority/telemetry - Current authority state
- GET /leto/authority/shadow-queue - Pending shadow items
- GET /leto/authority/blocks - Recent authorization blocks
- GET /leto/authority/stream - SSE stream for real-time updates
"""

import os
import json
import asyncio
from datetime import datetime
from typing import List, Optional, AsyncGenerator
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/leto/authority", tags=["leto-authority"])

# Base paths for artifacts
ARTIFACTS_BASE = Path(os.environ.get("LETO_ARTIFACTS_PATH", "artifacts/leto"))
STATE_BASE = Path(os.environ.get("LETO_STATE_PATH", "state"))


class AuthorityTelemetry(BaseModel):
    constitution_version: str
    presence_state: str
    authority_mode: str
    corridor_level: str
    shadow_queue_depth: int
    last_revalidation: Optional[str] = None
    takeover_active: bool
    timestamp: str


class ShadowQueueItem(BaseModel):
    id: str
    created_at: str
    proposal_type: str
    proposal_summary: str
    gate_status: Optional[str] = None
    awaiting_approval: bool


class AuthorizationBlock(BaseModel):
    id: str
    timestamp: str
    blocked_action: str
    reason: str
    corridor_level: str
    resolution: Optional[str] = None


def load_json_file(path: Path) -> Optional[dict]:
    """Load JSON file if it exists."""
    try:
        if path.exists():
            with open(path, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def get_presence_state() -> dict:
    """Load presence state from file or return defaults."""
    state_file = STATE_BASE / "presence_state.json"
    state = load_json_file(state_file)
    if state:
        return state
    return {
        "presence_state": "active",
        "authority_mode": "autonomous",
        "last_activity": datetime.utcnow().isoformat() + "Z"
    }


def get_corridor_status() -> dict:
    """Load corridor status from file or return defaults."""
    corridor_file = STATE_BASE / "corridor_status.json"
    status = load_json_file(corridor_file)
    if status:
        return status
    return {
        "level": "green",
        "takeover_active": False,
        "last_updated": datetime.utcnow().isoformat() + "Z"
    }


def scan_shadow_queue() -> List[dict]:
    """Scan shadow queue directory for pending items."""
    shadow_dir = ARTIFACTS_BASE / "shadow_queue"
    items = []

    if not shadow_dir.exists():
        return items

    for item_dir in shadow_dir.iterdir():
        if item_dir.is_dir():
            # Look for proposal files
            for proposal_name in ["proposal.json", "work_order.json", "operating_decision.json", "policy_decision.json"]:
                proposal_file = item_dir / proposal_name
                if proposal_file.exists():
                    proposal = load_json_file(proposal_file)
                    gate_verdict = load_json_file(item_dir / "gate_verdict.json")

                    items.append({
                        "id": item_dir.name,
                        "created_at": datetime.fromtimestamp(proposal_file.stat().st_mtime).isoformat() + "Z",
                        "proposal_type": proposal_name.replace(".json", ""),
                        "proposal_summary": proposal.get("summary", proposal.get("title", "Unknown")) if proposal else "Unknown",
                        "gate_status": gate_verdict.get("status") if gate_verdict else None,
                        "awaiting_approval": gate_verdict is None or gate_verdict.get("status") == "pending"
                    })
                    break

    return sorted(items, key=lambda x: x["created_at"], reverse=True)


@router.get("/telemetry", response_model=AuthorityTelemetry)
def get_authority_telemetry():
    """Get current LETO authority telemetry."""
    presence = get_presence_state()
    corridor = get_corridor_status()
    shadow_items = scan_shadow_queue()

    # Check for recent revalidation
    reval_dir = ARTIFACTS_BASE / "revalidation"
    last_reval = None
    if reval_dir.exists():
        reval_dirs = sorted(reval_dir.iterdir(), reverse=True)
        if reval_dirs:
            last_reval = reval_dirs[0].name

    return AuthorityTelemetry(
        constitution_version="1.1.0",
        presence_state=presence.get("presence_state", "unknown"),
        authority_mode=presence.get("authority_mode", "unknown"),
        corridor_level=corridor.get("level", "unknown"),
        shadow_queue_depth=len(shadow_items),
        last_revalidation=last_reval,
        takeover_active=corridor.get("takeover_active", False),
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


@router.get("/shadow-queue", response_model=List[ShadowQueueItem])
def get_shadow_queue():
    """Get all pending shadow queue items."""
    items = scan_shadow_queue()
    return [ShadowQueueItem(**item) for item in items]


@router.get("/blocks", response_model=List[AuthorizationBlock])
def get_authorization_blocks(limit: int = 20):
    """Get recent authorization blocks."""
    # For now, return mock data - in production this would scan block logs
    blocks = [
        AuthorizationBlock(
            id="block_001",
            timestamp=datetime.utcnow().isoformat() + "Z",
            blocked_action="execute_patchpack",
            reason="Takeover mode active - no execution allowed",
            corridor_level="red",
            resolution=None
        )
    ]
    return blocks[:limit]


async def event_generator() -> AsyncGenerator[str, None]:
    """Generate SSE events for authority updates."""
    last_telemetry = None

    while True:
        try:
            # Get current telemetry
            presence = get_presence_state()
            corridor = get_corridor_status()
            shadow_items = scan_shadow_queue()

            current = {
                "presence_state": presence.get("presence_state"),
                "authority_mode": presence.get("authority_mode"),
                "corridor_level": corridor.get("level"),
                "shadow_queue_depth": len(shadow_items),
                "takeover_active": corridor.get("takeover_active", False),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            # Only emit if changed
            if current != last_telemetry:
                yield f"event: authority_update\ndata: {json.dumps(current)}\n\n"
                last_telemetry = current.copy()
            else:
                # Heartbeat
                yield f"event: heartbeat\ndata: {json.dumps({'ts': datetime.utcnow().isoformat()})}\n\n"

            await asyncio.sleep(2)

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            await asyncio.sleep(5)


@router.get("/stream")
async def stream_authority_events():
    """SSE stream for real-time authority updates."""
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
