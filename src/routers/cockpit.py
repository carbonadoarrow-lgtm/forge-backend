"""
Cockpit API router for Authority, Shadow Queue, and Presence endpoints.
Read-only endpoints for the operator cockpit.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/cockpit", tags=["cockpit"])


# ============ AUTHORITY ============

class AuthorityBlock(BaseModel):
    id: str
    timestamp: str
    contract_type: str
    reason: str
    approvals_required: int
    artifact_link: Optional[str] = None
    approved: bool = False


class AuthorityStatus(BaseModel):
    presence_state: str  # NORMAL, WARN, TAKEOVER
    authority_mode: str  # founder, delegated, autonomous
    corridor_level: str  # green, yellow, red
    recent_blocks: List[AuthorityBlock]


@router.get("/authority/status", response_model=AuthorityStatus)
def get_authority_status():
    """Get current authority status and recent blocks."""
    now = datetime.utcnow()

    # Mock data - replace with real data from LETO/validator
    return AuthorityStatus(
        presence_state="NORMAL",
        authority_mode="founder",
        corridor_level="green",
        recent_blocks=[
            AuthorityBlock(
                id="blk_001",
                timestamp=(now - timedelta(hours=2)).isoformat() + "Z",
                contract_type="INFRA_WRITE",
                reason="Attempted write to production config",
                approvals_required=2,
                artifact_link="/artifacts/blocks/blk_001.json",
                approved=True,
            ),
            AuthorityBlock(
                id="blk_002",
                timestamp=(now - timedelta(hours=5)).isoformat() + "Z",
                contract_type="FINANCIAL",
                reason="Transaction above threshold",
                approvals_required=3,
                artifact_link="/artifacts/blocks/blk_002.json",
                approved=False,
            ),
        ],
    )


@router.get("/authority/recent")
def get_recent_authority_events(limit: int = 20):
    """Get recent authority events."""
    now = datetime.utcnow()

    return {
        "events": [
            {
                "id": f"evt_{i}",
                "type": "authority_check",
                "timestamp": (now - timedelta(minutes=i * 15)).isoformat() + "Z",
                "contract_type": ["READ", "WRITE", "INFRA_WRITE", "FINANCIAL"][i % 4],
                "result": "allowed" if i % 3 != 0 else "blocked",
                "corridor": "green" if i % 4 != 0 else "yellow",
            }
            for i in range(min(limit, 20))
        ]
    }


# ============ SHADOW QUEUE ============

class ShadowQueueItem(BaseModel):
    id: str
    queued_at: str
    authority_mode: str
    contract_type: str
    blocked_reason: str
    approvals_required: int
    payload_preview: str
    status: str  # pending, approved, rejected, expired


@router.get("/shadow-queue/tail", response_model=List[ShadowQueueItem])
def get_shadow_queue_tail(n: int = 50):
    """Get the tail of the shadow queue (most recent blocked items)."""
    now = datetime.utcnow()

    # Mock data - replace with real shadow queue
    return [
        ShadowQueueItem(
            id=f"sq_{i}",
            queued_at=(now - timedelta(hours=i)).isoformat() + "Z",
            authority_mode="autonomous" if i % 2 == 0 else "delegated",
            contract_type=["INFRA_WRITE", "FINANCIAL", "DATA_EXPORT"][i % 3],
            blocked_reason="Requires founder approval" if i % 2 == 0 else "Above threshold limit",
            approvals_required=2 if i % 2 == 0 else 3,
            payload_preview=f"Action: modify_{['config', 'database', 'api'][i % 3]}",
            status=["pending", "approved", "rejected", "expired"][i % 4],
        )
        for i in range(min(n, 10))
    ]


@router.get("/shadow-queue/item/{item_id}")
def get_shadow_queue_item(item_id: str):
    """Get full details of a shadow queue item."""
    now = datetime.utcnow()

    return {
        "id": item_id,
        "queued_at": (now - timedelta(hours=1)).isoformat() + "Z",
        "authority_mode": "autonomous",
        "contract_type": "INFRA_WRITE",
        "blocked_reason": "Requires founder approval",
        "approvals_required": 2,
        "approvals_received": 0,
        "status": "pending",
        "payload": {
            "action": "modify_config",
            "target": "production.yaml",
            "changes": {"key": "value"},
        },
        "trace": {
            "origin": "autobuilder",
            "run_id": "ab_123456",
            "step": 5,
        },
    }


# ============ PRESENCE ============

class PresenceStatus(BaseModel):
    current_state: str  # NORMAL, WARN, TAKEOVER
    last_activity: str
    hours_since_activity: float
    next_threshold_hours: float
    corridor_constraints: dict
    founder_online: bool


@router.get("/presence/status", response_model=PresenceStatus)
def get_presence_status():
    """Get current presence/liveness status."""
    now = datetime.utcnow()
    last_activity = now - timedelta(hours=2, minutes=30)

    hours_since = (now - last_activity).total_seconds() / 3600

    # Determine state based on hours since activity
    if hours_since < 4:
        state = "NORMAL"
        next_threshold = 4
    elif hours_since < 12:
        state = "WARN"
        next_threshold = 12
    else:
        state = "TAKEOVER"
        next_threshold = 24

    return PresenceStatus(
        current_state=state,
        last_activity=last_activity.isoformat() + "Z",
        hours_since_activity=round(hours_since, 2),
        next_threshold_hours=next_threshold,
        corridor_constraints={
            "max_transaction": 1000 if state == "NORMAL" else 100,
            "infra_writes": state == "NORMAL",
            "autonomous_deploys": state == "NORMAL",
        },
        founder_online=True,
    )


@router.get("/presence/timeline")
def get_presence_timeline(hours: int = 24):
    """Get presence timeline for the past N hours."""
    now = datetime.utcnow()

    return {
        "timeline": [
            {
                "timestamp": (now - timedelta(hours=i)).isoformat() + "Z",
                "state": "NORMAL" if i < 4 else ("WARN" if i < 12 else "TAKEOVER"),
                "activity": "heartbeat" if i % 2 == 0 else "action",
            }
            for i in range(min(hours, 24))
        ]
    }


# ============ CORRIDORS ============

@router.get("/corridors/status")
def get_corridors_status():
    """Get current corridor status and constraints."""
    return {
        "current_corridor": "green",
        "corridors": {
            "green": {
                "active": True,
                "constraints": {
                    "max_transaction": 10000,
                    "infra_writes": True,
                    "autonomous_deploys": True,
                    "data_exports": True,
                },
            },
            "yellow": {
                "active": False,
                "constraints": {
                    "max_transaction": 1000,
                    "infra_writes": True,
                    "autonomous_deploys": False,
                    "data_exports": True,
                },
            },
            "red": {
                "active": False,
                "constraints": {
                    "max_transaction": 100,
                    "infra_writes": False,
                    "autonomous_deploys": False,
                    "data_exports": False,
                },
            },
        },
    }
