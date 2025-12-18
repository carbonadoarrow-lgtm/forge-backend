"""
Tests for Orunmila Events System.

Tests Events, Presence, Corridors, and Neuroplasticity subsystems.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orunmila.events import EventEmitter, Severity, build_event
from orunmila.lrm.presence import PresenceStateMachine, PresenceState
from orunmila.lrm.corridors import CorridorManager, CorridorLevel
from orunmila.neuroplasticity import EpisodeLogger, IntentDistiller, EpisodeType


def test_event_system():
    """Test event creation and emission."""
    print("Testing Events System...")

    # Create emitter with test store
    test_store_path = "data/test_events.jsonl"
    emitter = EventEmitter(store_path=test_store_path, use_default_policy=False)

    # Build and emit an event
    event = build_event(
        event_type="test.event",
        severity=Severity.INFO,
        observation="Test event created",
        implication="Testing events subsystem",
        constraints=["Test only", "No side effects"],
        choice_set=["Verify event", "Continue testing"],
        meta_clarifier="Part of automated test suite",
    )

    emitter.emit(event)

    # Verify event was stored
    recent_events = emitter.get_recent_events(limit=10)
    assert len(recent_events) > 0, "No events found in store"
    assert recent_events[0].event_type == "test.event", "Event type mismatch"

    # Clean up
    emitter.store.clear()
    Path(test_store_path).parent.rmdir()

    print("✓ Events system test passed")


def test_presence_system():
    """Test presence tracking and state machine."""
    print("Testing Presence System...")

    # Create test presence machine
    test_activity_path = "data/test_presence_activity.json"
    test_state_path = "data/test_presence_state.json"

    machine = PresenceStateMachine(
        activity_log_path=test_activity_path,
        state_path=test_state_path,
    )

    # Log activity
    machine.log_activity("test_activity")

    # Get status
    status = machine.get_status()
    assert status.state == PresenceState.NORMAL, "Expected NORMAL state"
    assert status.hours_since_last >= 0, "Invalid hours_since_last"

    # Force warn state
    machine.force_state(PresenceState.WARN)
    assert machine.get_current_state() == PresenceState.WARN, "State transition failed"

    # Clean up
    Path(test_activity_path).unlink(missing_ok=True)
    Path(test_state_path).unlink(missing_ok=True)

    print("✓ Presence system test passed")


def test_corridors_system():
    """Test corridors and dynamic configuration."""
    print("Testing Corridors System...")

    # Create test corridor manager
    test_config_path = "data/test_corridors.json"

    manager = CorridorManager(config_path=test_config_path)

    # Get current status
    status = manager.get_current_status()
    assert status.level == CorridorLevel.NORMAL, "Expected NORMAL level"

    # Set to WARN level
    manager.set_level(CorridorLevel.WARN)
    status = manager.get_current_status()
    assert status.level == CorridorLevel.WARN, "Level transition failed"
    assert status.config.max_parallel_tasks == 5, "Config not updated"

    # Check operation allowed
    allowed = manager.check_operation_allowed("parallel_tasks", count=3)
    assert allowed, "Operation should be allowed"

    disallowed = manager.check_operation_allowed("parallel_tasks", count=10)
    assert not disallowed, "Operation should be disallowed"

    # Clean up
    Path(test_config_path).unlink(missing_ok=True)

    print("✓ Corridors system test passed")


def test_neuroplasticity_system():
    """Test episode logging and intent distillation."""
    print("Testing Neuroplasticity System...")

    # Create test episode logger
    test_log_path = "data/test_episodes.jsonl"

    logger = EpisodeLogger(log_path=test_log_path)

    # Log episodes
    episode1 = logger.log_episode(
        episode_type=EpisodeType.CORRECTION,
        context={"correction": "Always use strict mode for critical operations"},
    )

    episode2 = logger.log_episode(
        episode_type=EpisodeType.PREFERENCE,
        context={"preference": "Prefer config-based approach over hardcoding"},
    )

    # Read episodes
    episodes = logger.read_all_episodes()
    assert len(episodes) == 2, f"Expected 2 episodes, found {len(episodes)}"

    # Test distiller
    distiller = IntentDistiller()
    intents = distiller.distill_from_episodes(episodes)

    assert len(intents) > 0, "No intents distilled"
    print(f"  Distilled {len(intents)} intent(s)")

    # Clean up
    Path(test_log_path).unlink(missing_ok=True)

    print("✓ Neuroplasticity system test passed")


def test_integrated_presence_corridors():
    """Test integrated presence + corridors sync."""
    print("Testing Presence + Corridors Integration...")

    # Create test instances
    test_activity_path = "data/test_integration_activity.json"
    test_state_path = "data/test_integration_state.json"
    test_config_path = "data/test_integration_corridors.json"

    presence = PresenceStateMachine(
        activity_log_path=test_activity_path,
        state_path=test_state_path,
    )

    corridors = CorridorManager(
        config_path=test_config_path,
        presence_state_machine=presence,
    )

    # Initially both should be NORMAL
    assert presence.get_current_state() == PresenceState.NORMAL
    assert corridors.get_current_status().level == CorridorLevel.NORMAL

    # Force presence to WARN
    presence.force_state(PresenceState.WARN)

    # Sync corridors
    corridors.sync_with_presence()

    # Corridors should now be WARN
    assert corridors.get_current_status().level == CorridorLevel.WARN
    print("  Corridors synced with presence state")

    # Clean up
    Path(test_activity_path).unlink(missing_ok=True)
    Path(test_state_path).unlink(missing_ok=True)
    Path(test_config_path).unlink(missing_ok=True)

    print("✓ Integration test passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Running Orunmila Events System Tests")
    print("=" * 60)

    try:
        test_event_system()
        test_presence_system()
        test_corridors_system()
        test_neuroplasticity_system()
        test_integrated_presence_corridors()

        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
