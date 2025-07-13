#!/usr/bin/env python3
"""
Test script to verify PostgreSQL migration functionality.
This script tests all database operations to ensure they work correctly.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import initialize_database, test_connection, close_pool
from database.operations import (
    # Guild config operations
    get_guild_config,
    set_guild_config,
    get_all_guild_config,
    # User infractions operations
    add_user_infraction,
    get_user_infractions,
    clear_user_infractions,
    # Appeals operations
    create_appeal,
    get_appeal,
    update_appeal_status,
    get_user_appeals,
    # Global bans operations
    add_global_ban,
    remove_global_ban,
    is_globally_banned,
    get_all_global_bans,
    # Moderation logs operations
    add_mod_log,
    get_mod_log,
    update_mod_log_reason,
    get_user_mod_logs,
    get_guild_mod_logs,
    # Guild settings operations
    get_guild_setting,
    set_guild_setting,
    # Log event toggles operations
    get_log_event_enabled,
    set_log_event_enabled,
    get_all_log_event_toggles,
    # Bot detection config operations
    get_botdetect_config,
    set_botdetect_config,
    get_all_botdetect_config,
    # User data operations
    get_user_data,
    set_user_data,
    update_user_data_field,
    delete_user_data,
)


# Colors for output
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    PURPLE = "\033[0;35m"
    CYAN = "\033[0;36m"
    NC = "\033[0m"  # No Color


def print_colored(message: str, color: str = Colors.NC):
    """Print a colored message."""
    print(f"{color}{message}{Colors.NC}")


def print_test_result(test_name: str, success: bool, details: str = ""):
    """Print test result with appropriate color."""
    status = "PASS" if success else "FAIL"
    color = Colors.GREEN if success else Colors.RED
    message = f"[{status}] {test_name}"
    if details:
        message += f" - {details}"
    print_colored(message, color)


async def test_database_connection():
    """Test basic database connectivity."""
    print_colored("Testing database connection...", Colors.BLUE)

    try:
        success = await test_connection()
        print_test_result("Database Connection", success)
        return success
    except Exception as e:
        print_test_result("Database Connection", False, str(e))
        return False


async def test_guild_config_operations():
    """Test guild configuration operations."""
    print_colored("Testing guild configuration operations...", Colors.BLUE)

    test_guild_id = 123456789
    test_key = "test_setting"
    test_value = "test_value"

    all_passed = True

    try:
        # Test setting a value
        success = await set_guild_config(test_guild_id, test_key, test_value)
        print_test_result("Set Guild Config", success)
        if not success:
            all_passed = False

        # Test getting the value
        retrieved_value = await get_guild_config(test_guild_id, test_key)
        success = retrieved_value == test_value
        print_test_result(
            "Get Guild Config",
            success,
            f"Expected: {test_value}, Got: {retrieved_value}",
        )
        if not success:
            all_passed = False

        # Test getting all config
        all_config = await get_all_guild_config(test_guild_id)
        success = test_key in all_config and all_config[test_key] == test_value
        print_test_result("Get All Guild Config", success)
        if not success:
            all_passed = False

        return all_passed

    except Exception as e:
        print_test_result("Guild Config Operations", False, str(e))
        return False


async def test_user_infractions_operations():
    """Test user infractions operations."""
    print_colored("Testing user infractions operations...", Colors.BLUE)

    test_guild_id = 123456789
    test_user_id = 987654321

    try:
        # Test adding an infraction
        infraction_id = await add_user_infraction(
            guild_id=test_guild_id,
            user_id=test_user_id,
            timestamp=datetime.now(timezone.utc),
            rule_violated="1",
            action_taken="WARN",
            reasoning="Test infraction",
        )
        success = infraction_id is not None
        print_test_result("Add User Infraction", success, f"ID: {infraction_id}")

        # Test getting infractions
        infractions = await get_user_infractions(test_guild_id, test_user_id)
        success = len(infractions) > 0
        print_test_result("Get User Infractions", success, f"Count: {len(infractions)}")

        # Test clearing infractions
        success = await clear_user_infractions(test_guild_id, test_user_id)
        print_test_result("Clear User Infractions", success)

        return True

    except Exception as e:
        print_test_result("User Infractions Operations", False, str(e))
        return False


async def test_appeals_operations():
    """Test appeals operations."""
    print_colored("Testing appeals operations...", Colors.BLUE)

    test_user_id = 987654321
    test_reason = "Test appeal"
    test_infraction = {"rule": "1", "action": "BAN"}

    try:
        # Test creating an appeal
        appeal_id = await create_appeal(test_user_id, test_reason, test_infraction)
        success = appeal_id is not None
        print_test_result("Create Appeal", success, f"ID: {appeal_id}")

        if appeal_id:
            # Test getting the appeal
            appeal = await get_appeal(appeal_id)
            success = appeal is not None and appeal["user_id"] == test_user_id
            print_test_result("Get Appeal", success)

            # Test updating appeal status
            success = await update_appeal_status(appeal_id, "accepted")
            print_test_result("Update Appeal Status", success)

            # Test getting user appeals
            user_appeals = await get_user_appeals(test_user_id)
            success = len(user_appeals) > 0
            print_test_result(
                "Get User Appeals", success, f"Count: {len(user_appeals)}"
            )

        return True

    except Exception as e:
        print_test_result("Appeals Operations", False, str(e))
        return False


async def test_global_bans_operations():
    """Test global bans operations."""
    print_colored("Testing global bans operations...", Colors.BLUE)

    test_user_id = 111222333

    try:
        # Test adding a global ban
        success = await add_global_ban(test_user_id, "Test ban")
        print_test_result("Add Global Ban", success)

        # Test checking if user is banned
        is_banned = await is_globally_banned(test_user_id)
        print_test_result("Check Global Ban", is_banned)

        # Test getting all global bans
        all_bans = await get_all_global_bans()
        success = test_user_id in all_bans
        print_test_result("Get All Global Bans", success, f"Count: {len(all_bans)}")

        # Test removing global ban
        success = await remove_global_ban(test_user_id)
        print_test_result("Remove Global Ban", success)

        return True

    except Exception as e:
        print_test_result("Global Bans Operations", False, str(e))
        return False


async def test_moderation_logs_operations():
    """Test moderation logs operations."""
    print_colored("Testing moderation logs operations...", Colors.BLUE)

    test_guild_id = 123456789
    test_moderator_id = 111111111
    test_target_id = 222222222

    try:
        # Test adding a mod log
        case_id = await add_mod_log(
            guild_id=test_guild_id,
            moderator_id=test_moderator_id,
            target_user_id=test_target_id,
            action_type="WARN",
            reason="Test moderation action",
        )
        success = case_id is not None
        print_test_result("Add Mod Log", success, f"Case ID: {case_id}")

        if case_id:
            # Test getting the mod log
            mod_log = await get_mod_log(case_id)
            success = mod_log is not None and mod_log["guild_id"] == test_guild_id
            print_test_result("Get Mod Log", success)

            # Test updating mod log reason
            success = await update_mod_log_reason(case_id, "Updated test reason")
            print_test_result("Update Mod Log Reason", success)

            # Test getting user mod logs
            user_logs = await get_user_mod_logs(test_guild_id, test_target_id)
            success = len(user_logs) > 0
            print_test_result("Get User Mod Logs", success, f"Count: {len(user_logs)}")

            # Test getting guild mod logs
            guild_logs = await get_guild_mod_logs(test_guild_id)
            success = len(guild_logs) > 0
            print_test_result(
                "Get Guild Mod Logs", success, f"Count: {len(guild_logs)}"
            )

        return True

    except Exception as e:
        print_test_result("Moderation Logs Operations", False, str(e))
        return False


async def test_settings_operations():
    """Test guild settings operations."""
    print_colored("Testing guild settings operations...", Colors.BLUE)

    test_guild_id = 123456789
    test_key = "test_log_setting"
    test_value = True

    all_passed = True

    try:
        # Test setting a guild setting
        success = await set_guild_setting(test_guild_id, test_key, test_value)
        print_test_result("Set Guild Setting", success)
        if not success:
            all_passed = False

        # Test getting the guild setting
        retrieved_value = await get_guild_setting(test_guild_id, test_key)
        success = retrieved_value == test_value
        print_test_result(
            "Get Guild Setting",
            success,
            f"Expected: {test_value}, Got: {retrieved_value}",
        )
        if not success:
            all_passed = False

        return all_passed

    except Exception as e:
        print_test_result("Guild Settings Operations", False, str(e))
        return False


async def test_log_event_toggles_operations():
    """Test log event toggles operations."""
    print_colored("Testing log event toggles operations...", Colors.BLUE)

    test_guild_id = 123456789
    test_event = "message_delete"

    try:
        # Test setting log event enabled
        success = await set_log_event_enabled(test_guild_id, test_event, False)
        print_test_result("Set Log Event Enabled", success)

        # Test getting log event enabled status
        is_enabled = await get_log_event_enabled(test_guild_id, test_event)
        success = is_enabled == False
        print_test_result(
            "Get Log Event Enabled", success, f"Expected: False, Got: {is_enabled}"
        )

        # Test getting all log event toggles
        all_toggles = await get_all_log_event_toggles(test_guild_id)
        success = test_event in all_toggles
        print_test_result(
            "Get All Log Event Toggles", success, f"Count: {len(all_toggles)}"
        )

        return True

    except Exception as e:
        print_test_result("Log Event Toggles Operations", False, str(e))
        return False


async def test_botdetect_config_operations():
    """Test bot detection configuration operations."""
    print_colored("Testing bot detection configuration operations...", Colors.BLUE)

    test_guild_id = 123456789
    test_key = "enabled"
    test_value = True

    all_passed = True

    try:
        # Test setting botdetect config
        success = await set_botdetect_config(test_guild_id, test_key, test_value)
        print_test_result("Set Botdetect Config", success)
        if not success:
            all_passed = False

        # Test getting botdetect config
        retrieved_value = await get_botdetect_config(test_guild_id, test_key)
        success = retrieved_value == test_value
        print_test_result(
            "Get Botdetect Config",
            success,
            f"Expected: {test_value}, Got: {retrieved_value}",
        )
        if not success:
            all_passed = False

        # Test getting all botdetect config
        all_config = await get_all_botdetect_config(test_guild_id)
        success = test_key in all_config
        print_test_result(
            "Get All Botdetect Config", success, f"Count: {len(all_config)}"
        )
        if not success:
            all_passed = False

        return all_passed

    except Exception as e:
        print_test_result("Botdetect Config Operations", False, str(e))
        return False


async def test_user_data_operations():
    """Test user data operations."""
    print_colored("Testing user data operations...", Colors.BLUE)

    test_user_id = 555666777
    test_data = {"organization": "Test Corp", "role": "Developer"}

    try:
        # Test setting user data
        success = await set_user_data(test_user_id, test_data)
        print_test_result("Set User Data", success)

        # Test getting user data
        retrieved_data = await get_user_data(test_user_id)
        success = retrieved_data == test_data
        print_test_result(
            "Get User Data", success, f"Expected: {test_data}, Got: {retrieved_data}"
        )

        # Test updating user data field
        success = await update_user_data_field(
            test_user_id, "department", "Engineering"
        )
        print_test_result("Update User Data Field", success)

        # Test deleting user data
        success = await delete_user_data(test_user_id)
        print_test_result("Delete User Data", success)

        return True

    except Exception as e:
        print_test_result("User Data Operations", False, str(e))
        return False


async def main():
    """Main test function."""
    print_colored("=== PostgreSQL Migration Test Suite ===", Colors.PURPLE)
    print_colored(
        "Testing all database operations to verify migration success", Colors.CYAN
    )
    print()

    # Check if database environment variables are set
    required_env_vars = ["DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        print_colored(
            f"Missing required environment variables: {', '.join(missing_vars)}",
            Colors.RED,
        )
        print_colored(
            "Please run the setup_postgresql.sh script first or set the variables manually",
            Colors.YELLOW,
        )
        return

    try:
        # Initialize database
        print_colored("Initializing database...", Colors.BLUE)
        await initialize_database()

        # Run all tests
        tests = [
            test_database_connection,
            test_guild_config_operations,
            test_user_infractions_operations,
            test_appeals_operations,
            test_global_bans_operations,
            test_moderation_logs_operations,
            test_settings_operations,
            test_log_event_toggles_operations,
            test_botdetect_config_operations,
            test_user_data_operations,
        ]

        passed_tests = 0
        total_tests = len(tests)

        for test_func in tests:
            print()
            try:
                success = await test_func()
                if success:
                    passed_tests += 1
            except Exception as e:
                print_test_result(test_func.__name__, False, f"Unexpected error: {e}")

        print()
        print_colored("=== Test Results ===", Colors.PURPLE)
        print_colored(
            f"Passed: {passed_tests}/{total_tests}",
            Colors.GREEN if passed_tests == total_tests else Colors.YELLOW,
        )

        if passed_tests == total_tests:
            print_colored(
                "🎉 All tests passed! PostgreSQL migration is successful.", Colors.GREEN
            )
        else:
            print_colored(
                f"⚠️  {total_tests - passed_tests} test(s) failed. Please check the issues above.",
                Colors.YELLOW,
            )

    except Exception as e:
        print_colored(f"Test suite failed: {e}", Colors.RED)
        import traceback

        traceback.print_exc()

    finally:
        # Close database connection
        await close_pool()


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv

    load_dotenv(".env")

    asyncio.run(main())
