"""
Orunmila Events API Router - SSE and REST endpoints for Events system.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, AsyncGenerator, Dict, Any
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

# Import Orunmila subsystems
try:
    from orunmila.events import EventEmitter, EventEnvelope
    from orunmila.lrm.presence import PresenceStateMachine
    from orunmila.lrm.corridors import CorridorManager
    from orunmila.neuroplasticity import EpisodeLogger
    from orunmila.return_brief import ReturnBriefGenerator
    ORUNMILA_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Orunmila modules not available: {e}")
    ORUNMILA_AVAILABLE = False

router = APIRouter(prefix="/orunmila/events", tags=["orunmila-events"])

# Global Orunmila instances (initialized on first use)
_event_emitter = None
_presence_machine = None
_corridor_manager = None
_episode_logger = None
_return_brief_generator = None


def get_event_emitter() -> EventEmitter:
    """Get or create EventEmitter instance."""
    global _event_emitter
    if _event_emitter is None and ORUNMILA_AVAILABLE:
        _event_emitter = EventEmitter()
    return _event_emitter


def get_presence_machine() -> PresenceStateMachine:
    """Get or create PresenceStateMachine instance."""
    global _presence_machine
    if _presence_machine is None and ORUNMILA_AVAILABLE:
        _presence_machine = PresenceStateMachine(event_emitter=get_event_emitter())
    return _presence_machine


def get_corridor_manager() -> CorridorManager:
    """Get or create CorridorManager instance."""
    global _corridor_manager
    if _corridor_manager is None and ORUNMILA_AVAILABLE:
        _corridor_manager = CorridorManager(presence_state_machine=get_presence_machine())
    return _corridor_manager


def get_episode_logger() -> EpisodeLogger:
    """Get or create EpisodeLogger instance."""
    global _episode_logger
    if _episode_logger is None and ORUNMILA_AVAILABLE:
        _episode_logger = EpisodeLogger()
    return _episode_logger


def get_return_brief_generator() -> ReturnBriefGenerator:
    """Get or create ReturnBriefGenerator instance."""
    global _return_brief_generator
    if _return_brief_generator is None and ORUNMILA_AVAILABLE:
        from orunmila.neuroplasticity import IntentApplicator
        _return_brief_generator = ReturnBriefGenerator(
            presence_state_machine=get_presence_machine(),
            event_emitter=get_event_emitter(),
            corridor_manager=get_corridor_manager(),
            neuroplasticity_applicator=IntentApplicator(event_emitter=get_event_emitter()),
        )
    return _return_brief_generator


# ============================================================================
# Events API
# ============================================================================

@router.get("/stream")
async def stream_events():
    """
    Server-Sent Events (SSE) endpoint for real-time event streaming.

    Streams events as they occur to connected clients.
    """
    if not ORUNMILA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Orunmila subsystem not available")

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events."""
        emitter = get_event_emitter()
        last_event_count = emitter.store.count()

        while True:
            try:
                # Check for new events
                current_count = emitter.store.count()
                if current_count > last_event_count:
                    # Get new events
                    new_events = emitter.get_recent_events(limit=current_count - last_event_count)
                    for event in new_events:
                        yield f"data: {json.dumps(event.to_dict())}\n\n"
                    last_event_count = current_count

                # Keep connection alive
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error in event stream: {e}")
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/recent")
def get_recent_events(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get recent events.

    Args:
        limit: Maximum number of events to return (default: 100)

    Returns:
        List of events (newest first)
    """
    if not ORUNMILA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Orunmila subsystem not available")

    emitter = get_event_emitter()
    events = emitter.get_recent_events(limit=limit)
    return [event.to_dict() for event in events]


@router.get("/by-type/{event_type}")
def get_events_by_type(event_type: str) -> List[Dict[str, Any]]:
    """
    Get events by type.

    Args:
        event_type: Event type to filter by

    Returns:
        List of matching events
    """
    if not ORUNMILA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Orunmila subsystem not available")

    emitter = get_event_emitter()
    events = emitter.get_events_by_type(event_type)
    return [event.to_dict() for event in events]


@router.get("/count")
def get_event_count() -> Dict[str, int]:
    """
    Get total event count.

    Returns:
        Total event count
    """
    if not ORUNMILA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Orunmila subsystem not available")

    emitter = get_event_emitter()
    return {"count": emitter.store.count()}


# ============================================================================
# Presence API
# ============================================================================

@router.get("/presence/status")
def get_presence_status() -> Dict[str, Any]:
    """
    Get current presence status.

    Returns:
        Presence status with state, last activity, and hours elapsed
    """
    if not ORUNMILA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Orunmila subsystem not available")

    machine = get_presence_machine()
    status = machine.get_status()
    return status.to_dict()


@router.post("/presence/activity")
def log_presence_activity(activity_type: str = "manual"):
    """
    Log founder activity.

    Args:
        activity_type: Type of activity (default: "manual")

    Returns:
        Updated presence status
    """
    if not ORUNMILA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Orunmila subsystem not available")

    machine = get_presence_machine()
    machine.log_activity(activity_type)

    # Sync corridors with new state
    corridor_manager = get_corridor_manager()
    corridor_manager.sync_with_presence()

    status = machine.get_status()
    return status.to_dict()


@router.post("/presence/check")
def check_presence_thresholds():
    """
    Check and transition presence state if needed.

    Should be called periodically by a scheduler.

    Returns:
        Updated presence status
    """
    if not ORUNMILA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Orunmila subsystem not available")

    machine = get_presence_machine()
    machine.check_and_transition()

    # Sync corridors with new state
    corridor_manager = get_corridor_manager()
    corridor_manager.sync_with_presence()

    status = machine.get_status()
    return status.to_dict()


# ============================================================================
# Corridors API
# ============================================================================

@router.get("/corridors/status")
def get_corridor_status() -> Dict[str, Any]:
    """
    Get current corridor status.

    Returns:
        Corridor status with level and configuration
    """
    if not ORUNMILA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Orunmila subsystem not available")

    manager = get_corridor_manager()
    status = manager.get_current_status()
    return status.to_dict()


@router.get("/corridors/config")
def get_corridor_config() -> Dict[str, Any]:
    """
    Get current corridor configuration.

    Returns:
        Corridor configuration
    """
    if not ORUNMILA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Orunmila subsystem not available")

    manager = get_corridor_manager()
    config = manager.get_current_config()
    return config.to_dict()


@router.post("/corridors/sync")
def sync_corridors_with_presence():
    """
    Sync corridor level with presence state.

    Returns:
        Updated corridor status
    """
    if not ORUNMILA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Orunmila subsystem not available")

    manager = get_corridor_manager()
    manager.sync_with_presence()

    status = manager.get_current_status()
    return status.to_dict()


# ============================================================================
# Return Brief API
# ============================================================================

@router.post("/return-brief/generate")
def generate_return_brief() -> Dict[str, str]:
    """
    Generate return brief.

    Returns:
        Path to generated brief file
    """
    if not ORUNMILA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Orunmila subsystem not available")

    generator = get_return_brief_generator()
    brief_path = generator.generate_brief()
    return {"brief_path": brief_path}


@router.get("/return-brief/json")
def get_return_brief_json() -> Dict[str, Any]:
    """
    Get return brief as JSON.

    Returns:
        Return brief data
    """
    if not ORUNMILA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Orunmila subsystem not available")

    generator = get_return_brief_generator()
    return generator.generate_json_brief()


# ============================================================================
# Healthcheck
# ============================================================================

@router.get("/health")
def health_check() -> Dict[str, Any]:
    """
    Health check for Orunmila Events system.

    Returns:
        Health status
    """
    return {
        "status": "operational" if ORUNMILA_AVAILABLE else "unavailable",
        "subsystems": {
            "events": ORUNMILA_AVAILABLE,
            "presence": ORUNMILA_AVAILABLE,
            "corridors": ORUNMILA_AVAILABLE,
            "neuroplasticity": ORUNMILA_AVAILABLE,
        },
    }
