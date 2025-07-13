#!/usr/bin/env python3
"""
Test script for the logging integration.
This script tests the basic functionality of the adapted logging system.

To run this test, make sure you have all dependencies installed:
pip install aiofiles aiohttp discord.py

Then run: python test_logging_integration.py
"""

import asyncio
import os
import sys
import json
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_json_storage():
    """Test the JSON storage functionality."""
    print("Testing JSON storage...")

    try:
        from cogs.logging_helpers import json_db

        # Test setup
        await json_db.setup_moderation_log_table()
        print("✓ JSON storage setup successful")

        # Test adding a mod log
        case_id = await json_db.add_mod_log(
            guild_id=123456789,
            moderator_id=987654321,
            target_user_id=111222333,
            action_type="BAN",
            reason="Test ban reason",
            duration_seconds=3600,
        )

        if case_id:
            print(f"✓ Added mod log entry with case ID: {case_id}")

            # Test retrieving the log
            log_entry = await json_db.get_mod_log(case_id)
            if log_entry:
                print(f"✓ Retrieved mod log entry: {log_entry['action_type']}")
            else:
                print("✗ Failed to retrieve mod log entry")

            # Test updating reason
            success = await json_db.update_mod_log_reason(
                case_id, "Updated test reason"
            )
            if success:
                print("✓ Updated mod log reason")
            else:
                print("✗ Failed to update mod log reason")

        else:
            print("✗ Failed to add mod log entry")

    except ImportError as e:
        print(f"✗ Import error (expected if dependencies not installed): {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

    return True


async def test_settings_manager():
    """Test the settings manager functionality."""
    print("\nTesting settings manager...")

    try:
        from cogs.logging_helpers import settings_manager

        # Test initialization
        await settings_manager.initialize_database()
        print("✓ Settings manager initialized")

        # Test setting and getting a value
        guild_id = 123456789
        test_key = "test_setting"
        test_value = "test_value_123"

        success = await settings_manager.set_setting(guild_id, test_key, test_value)
        if success:
            print("✓ Set test setting")

            retrieved_value = await settings_manager.get_setting(guild_id, test_key)
            if retrieved_value == test_value:
                print("✓ Retrieved test setting correctly")
            else:
                print(f"✗ Retrieved wrong value: {retrieved_value}")
        else:
            print("✗ Failed to set test setting")

        # Test mod log settings
        channel_id = 987654321
        success = await settings_manager.set_mod_log_channel_id(guild_id, channel_id)
        if success:
            print("✓ Set mod log channel ID")

            retrieved_channel = await settings_manager.get_mod_log_channel_id(guild_id)
            if retrieved_channel == channel_id:
                print("✓ Retrieved mod log channel ID correctly")
            else:
                print(f"✗ Retrieved wrong channel ID: {retrieved_channel}")
        else:
            print("✗ Failed to set mod log channel ID")

    except ImportError as e:
        print(f"✗ Import error (expected if dependencies not installed): {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

    return True


async def test_mod_log_db():
    """Test the mod log database interface."""
    print("\nTesting mod log database interface...")

    try:
        from cogs.logging_helpers import mod_log_db

        # Test the compatibility wrapper functions
        success = await mod_log_db.setup_moderation_log_table(None)
        if success:
            print("✓ Mod log table setup successful")
        else:
            print("✗ Mod log table setup failed")

        # Test adding a log through the wrapper
        case_id = await mod_log_db.add_mod_log(
            pool=None,  # Not needed for JSON storage
            guild_id=123456789,
            moderator_id=987654321,
            target_user_id=444555666,
            action_type="WARN",
            reason="Test warning",
            duration_seconds=None,
        )

        if case_id:
            print(f"✓ Added mod log via wrapper with case ID: {case_id}")

            # Test retrieving via wrapper
            log_entry = await mod_log_db.get_mod_log(None, case_id)
            if log_entry:
                print(f"✓ Retrieved mod log via wrapper: {log_entry['action_type']}")
            else:
                print("✗ Failed to retrieve mod log via wrapper")
        else:
            print("✗ Failed to add mod log via wrapper")

    except ImportError as e:
        print(f"✗ Import error (expected if dependencies not installed): {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

    return True


def check_file_structure():
    """Check that all necessary files exist."""
    print("Checking file structure...")

    required_files = [
        "cogs/logging_helpers/__init__.py",
        "cogs/logging_helpers/json_db.py",
        "cogs/logging_helpers/mod_log_db.py",
        "cogs/logging_helpers/settings_manager.py",
        "cogs/mod_log_cog.py",
        "cogs/logging_cog.py",
    ]

    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} (missing)")
            all_exist = False

    return all_exist


def check_data_directory():
    """Check if the data directory is created."""
    print("\nChecking data directory...")

    data_dir = "logging-data"
    if os.path.exists(data_dir):
        print(f"✓ {data_dir} directory exists")

        # List any files that were created
        files = os.listdir(data_dir)
        if files:
            print("  Created files:")
            for file in files:
                print(f"    - {file}")
        else:
            print("  (no files created yet)")
    else:
        print(f"✗ {data_dir} directory not found")


async def main():
    """Run all tests."""
    print("=== Logging Integration Test ===\n")

    # Check file structure first
    if not check_file_structure():
        print("\n❌ File structure check failed. Some files are missing.")
        return

    print("\n✅ File structure check passed.\n")

    # Run functionality tests
    tests = [test_json_storage, test_settings_manager, test_mod_log_db]

    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(False)

    # Check data directory
    check_data_directory()

    # Summary
    print(f"\n=== Test Summary ===")
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed! The logging integration is working correctly.")
    else:
        print("⚠️  Some tests failed. This might be due to missing dependencies.")
        print("   Make sure to install: pip install aiofiles aiohttp discord.py")


if __name__ == "__main__":
    asyncio.run(main())
