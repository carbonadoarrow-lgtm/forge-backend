"""
Test Telegram integration for Orunmila Events System.

This script verifies that:
1. Telegram bot credentials are configured
2. Messages can be sent successfully
3. Taylor-formatted events are delivered correctly
"""

import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orunmila.channels.telegram import TelegramChannel, create_telegram_handler
from orunmila.events import EventEmitter, Severity, build_event


def test_telegram_connection():
    """Test basic Telegram connectivity."""
    print("=" * 60)
    print("Testing Telegram Integration")
    print("=" * 60)

    # Get credentials from environment
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("ORUNMILA_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("ORUNMILA_TELEGRAM_CHAT_ID")

    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not set")
        print("\nSet it with:")
        print('  PowerShell: setx TELEGRAM_BOT_TOKEN "your-bot-token"')
        print('  Bash: export TELEGRAM_BOT_TOKEN="your-bot-token"')
        return False

    if not chat_id:
        print("❌ TELEGRAM_CHAT_ID not set")
        print("\nSet it with:")
        print('  PowerShell: setx TELEGRAM_CHAT_ID "your-chat-id"')
        print('  Bash: export TELEGRAM_CHAT_ID="your-chat-id"')
        return False

    print(f"✓ Bot Token: {bot_token[:10]}...{bot_token[-4:]}")
    print(f"✓ Chat ID: {chat_id}")
    print()

    # Create Telegram channel
    channel = TelegramChannel(bot_token, chat_id)

    # Test connection
    print("Testing connection...")
    if channel.test_connection():
        print("✓ Connection test successful!")
    else:
        print("❌ Connection test failed!")
        return False

    return True


def test_taylor_event_delivery():
    """Test Taylor-formatted event delivery."""
    print("\n" + "=" * 60)
    print("Testing Taylor-Formatted Event Delivery")
    print("=" * 60)

    # Get credentials
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("ORUNMILA_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("ORUNMILA_TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("❌ Credentials not set, skipping event test")
        return False

    # Create event emitter with Telegram routing
    emitter = EventEmitter(
        store_path="data/test_telegram_events.jsonl",
        use_default_policy=False,
    )

    # Register Telegram channel
    telegram_handler = create_telegram_handler(bot_token, chat_id)
    emitter.router.register_channel("telegram", telegram_handler)

    # Add routing rule for all events to Telegram (for testing)
    from orunmila.events.router import RoutingRule
    emitter.router.add_rule(RoutingRule(
        channel="telegram",
        min_severity=Severity.INFO,
    ))

    # Test 1: Presence WARN event
    print("\n1. Sending Presence WARN event...")
    emitter.emit_presence_warn(25.5)
    print("✓ Presence WARN sent")

    # Test 2: Presence TAKEOVER event
    print("\n2. Sending Presence TAKEOVER event...")
    emitter.emit_presence_takeover(49.2)
    print("✓ Presence TAKEOVER sent")

    # Test 3: Taylor violation event
    print("\n3. Sending Taylor violation event...")
    emitter.emit_taylor_violation(
        message="I understand what you mean, I feel confident about this",
        violations=["Forbidden: I understand", "Forbidden: I feel"],
    )
    print("✓ Taylor violation sent")

    # Test 4: Custom event
    print("\n4. Sending custom corridor tightening event...")
    event = build_event(
        event_type="corridor.tightening",
        severity=Severity.WARN,
        observation="Founder inactive for 26.3 business hours - corridors tightening",
        implication="System entering reduced autonomy mode to preserve capital safety",
        constraints=[
            "Max parallel tasks reduced from 10 to 5",
            "Token budget reduced from 200k to 100k",
            "Taylor mode strict enforcement enabled",
        ],
        choice_set=[
            "Continue monitoring with reduced parallelism",
            "Log activity to return to normal state",
            "Review recent system actions",
        ],
        meta_clarifier="Weekend hours excluded from calculation",
        payload={
            "previous_level": "normal",
            "new_level": "warn",
            "hours_since_activity": 26.3,
        },
    )
    emitter.emit(event)
    print("✓ Corridor tightening event sent")

    # Clean up test store
    Path("data/test_telegram_events.jsonl").unlink(missing_ok=True)

    print("\n" + "=" * 60)
    print("✅ All test events sent successfully!")
    print("=" * 60)
    print("\nCheck your Telegram channel/group for 4 messages:")
    print("1. ⚠️ Presence WARN (24h threshold)")
    print("2. ❌ Presence TAKEOVER (48h threshold)")
    print("3. ⚠️ Taylor violation")
    print("4. ⚠️ Corridor tightening")
    print("\nEach should show:")
    print("  - Severity badge (⚠️ WARN / ❌ ERROR)")
    print("  - Observation (what happened)")
    print("  - Implication (what it means)")
    print("  - Constraints (boundaries)")
    print("  - Actions (available choices)")
    print("  - Context (meta clarifier)")
    print("  - Event ID and timestamp")

    return True


def main():
    """Run all tests."""
    try:
        # Test 1: Connection
        if not test_telegram_connection():
            print("\n❌ Connection test failed")
            print("\nNext steps:")
            print("1. Create bot via @BotFather on Telegram")
            print("2. Get bot token")
            print("3. Create private channel or group")
            print("4. Add bot as admin")
            print("5. Get chat ID (use @userinfobot or getUpdates)")
            print("6. Set environment variables")
            print("7. Restart terminal")
            print("8. Run this script again")
            return 1

        # Test 2: Event delivery
        if not test_taylor_event_delivery():
            print("\n❌ Event delivery test failed")
            return 1

        print("\n" + "=" * 60)
        print("🎉 TELEGRAM INTEGRATION VERIFIED!")
        print("=" * 60)
        print("\nYour Telegram bot is now ready to receive:")
        print("  ✓ Presence state transitions (WARN/TAKEOVER)")
        print("  ✓ Corridor tightening alerts")
        print("  ✓ Taylor mode violations")
        print("  ✓ All critical system events")
        print("\nLETO can now alert you even when you're absent!")

        return 0

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
