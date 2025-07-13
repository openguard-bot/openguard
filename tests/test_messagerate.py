#!/usr/bin/env python3
"""
Test script for the MessageRateCog functionality.
This script tests the core logic without requiring a full Discord bot setup.
Note: The cog uses Singapore Time (UTC+8) for all operations.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from collections import deque, defaultdict

# Add the project root to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# Mock discord.utils.timezone for testing
class MockTimezone:
    class utc:
        pass


class MockDiscordUtils:
    timezone = MockTimezone()


# Mock the discord module for testing
class MockDiscord:
    utils = MockDiscordUtils()
    Message = type("Message", (), {})
    Interaction = type("Interaction", (), {})
    TextChannel = type("TextChannel", (), {})


sys.modules["discord"] = MockDiscord()
sys.modules["discord.ext"] = type(sys)("discord.ext")
sys.modules["discord.ext.commands"] = type(sys)("commands")
sys.modules["discord.ext.tasks"] = type(sys)("tasks")
app_commands_module = type(
    "app_commands",
    (),
    {
        "Choice": type(
            "Choice",
            (),
            {
                "__init__": lambda self, name, value: None,
                "__class_getitem__": classmethod(lambda cls, item: cls),
            },
        ),
        "Group": lambda *a, **k: type(
            "DummyGroup",
            (),
            {"command": lambda *a, **k: (lambda f: f)},
        )(),
        "describe": lambda *a, **k: (lambda f: f),
        "choices": lambda *a, **k: (lambda f: f),
        "checks": type(
            "checks",
            (),
            {"has_permissions": lambda **kwargs: (lambda f: f)},
        ),
    },
)
sys.modules["discord.app_commands"] = app_commands_module
setattr(sys.modules["discord"], "app_commands", app_commands_module)
commands_module = sys.modules["discord.ext.commands"]
commands_module.Cog = type("Cog", (), {"listener": lambda *a, **k: (lambda f: f)})
commands_module.Bot = object


def fake_loop(*args, **kwargs):
    def decorator(func):
        class FakeTask:
            def start(self):
                pass

            def cancel(self):
                pass

            def before_loop(self, func2):
                return func2

            def after_loop(self, func2):
                return func2

        return FakeTask()

    return decorator


sys.modules["discord.ext.tasks"].loop = fake_loop

# Now we can import our cog
from cogs.messagerate import MessageRateCog


class TestMessageRateCog:
    """Test class for MessageRateCog functionality."""

    def __init__(self):
        # Create a mock bot
        self.bot = None
        self.cog = MessageRateCog(self.bot)
        # Stop the actual task loop for testing
        self.cog.rate_monitor.cancel()

    def test_calculate_target_slowmode(self):
        """Test the slowmode calculation logic."""
        print("Testing slowmode calculation...")

        # Test high activity
        high_rate = self.cog.calculate_target_slowmode(15)  # 15 msg/min
        assert high_rate == 5, f"Expected 5s for high rate, got {high_rate}s"
        print("✓ High activity rate calculation correct")

        # Test medium activity
        medium_rate = self.cog.calculate_target_slowmode(5)  # 5 msg/min
        assert medium_rate == 2, f"Expected 2s for medium rate, got {medium_rate}s"
        print("✓ Medium activity rate calculation correct")

        # Test low activity
        low_rate = self.cog.calculate_target_slowmode(1)  # 1 msg/min
        assert low_rate == 0, f"Expected 0s for low rate, got {low_rate}s"
        print("✓ Low activity rate calculation correct")

    def test_get_activity_level(self):
        """Test the activity level classification."""
        print("\nTesting activity level classification...")

        # Test high activity
        high_level = self.cog.get_activity_level(15)
        assert high_level == "High", f"Expected 'High', got '{high_level}'"
        print("✓ High activity level classification correct")

        # Test medium activity
        medium_level = self.cog.get_activity_level(5)
        assert medium_level == "Medium", f"Expected 'Medium', got '{medium_level}'"
        print("✓ Medium activity level classification correct")

        # Test low activity
        low_level = self.cog.get_activity_level(1)
        assert low_level == "Low", f"Expected 'Low', got '{low_level}'"
        print("✓ Low activity level classification correct")

    def test_message_tracking(self):
        """Test message timestamp tracking."""
        print("\nTesting message tracking...")

        channel_id = 12345
        current_time = datetime.now()

        # Simulate adding messages
        for i in range(5):
            self.cog.message_history[channel_id].append(
                current_time - timedelta(seconds=i * 10)
            )

        assert (
            len(self.cog.message_history[channel_id]) == 5
        ), "Message history should contain 5 messages"
        print("✓ Message tracking works correctly")

        # Test that old messages are filtered out
        analysis_cutoff = current_time - timedelta(seconds=30)
        recent_messages = [
            timestamp
            for timestamp in self.cog.message_history[channel_id]
            if timestamp >= analysis_cutoff
        ]

        # Should have 3 messages (0s, 10s, 20s ago)
        assert (
            len(recent_messages) == 3
        ), f"Expected 3 recent messages, got {len(recent_messages)}"
        print("✓ Message filtering by time works correctly")

    def test_configuration_constants(self):
        """Test that configuration constants are reasonable."""
        print("\nTesting configuration constants...")

        assert (
            self.cog.HIGH_RATE_THRESHOLD > self.cog.LOW_RATE_THRESHOLD
        ), "High rate threshold should be greater than low rate"
        assert (
            self.cog.HIGH_RATE_SLOWMODE > self.cog.LOW_RATE_SLOWMODE
        ), "High rate slowmode should be greater than low rate"
        assert (
            self.cog.LOW_RATE_SLOWMODE > self.cog.NO_SLOWMODE
        ), "Low rate slowmode should be greater than no slowmode"
        assert self.cog.ANALYSIS_WINDOW > 0, "Analysis window should be positive"
        assert self.cog.CHECK_INTERVAL > 0, "Check interval should be positive"

        print("✓ Configuration constants are reasonable")

    def run_all_tests(self):
        """Run all tests."""
        print("Running MessageRateCog tests...\n")

        try:
            self.test_calculate_target_slowmode()
            self.test_get_activity_level()
            self.test_message_tracking()
            self.test_configuration_constants()

            print("\n✅ All tests passed!")
            return True

        except AssertionError as e:
            print(f"\n❌ Test failed: {e}")
            return False
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            return False


def main():
    """Main test function."""
    tester = TestMessageRateCog()
    success = tester.run_all_tests()

    if success:
        print("\nThe MessageRateCog appears to be working correctly!")
        print(
            "You can now test it in your Discord server using the /message ratelimit command."
        )
    else:
        print("\nSome tests failed. Please check the implementation.")

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
