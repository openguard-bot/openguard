#!/usr/bin/env python3
"""
Migration script to transfer data from JSON files to PostgreSQL database.
This script reads all existing JSON data and migrates it to the new PostgreSQL schema.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import initialize_database, close_pool
from database.operations import (
    set_guild_config,
    add_user_infraction,
    add_global_ban,
    add_mod_log,
    set_guild_setting,
    set_log_event_enabled,
    set_botdetect_config,
    set_user_data,
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


def load_json_file(file_path: str) -> Any:
    """Load data from a JSON file."""
    if not os.path.exists(file_path):
        print_colored(f"File not found: {file_path}", Colors.YELLOW)
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return None
            return json.loads(content)
    except Exception as e:
        print_colored(f"Error loading {file_path}: {e}", Colors.RED)
        return None


async def migrate_guild_config():
    """Migrate guild configuration data."""
    print_colored("Migrating guild configuration...", Colors.BLUE)

    config_path = "wdiscordbot-json-data/guild_config.json"
    config_data = load_json_file(config_path)

    if not config_data:
        print_colored("No guild config data to migrate", Colors.YELLOW)
        return

    migrated_count = 0
    for guild_id_str, guild_config in config_data.items():
        guild_id = int(guild_id_str)

        for key, value in guild_config.items():
            success = await set_guild_config(guild_id, key, value)
            if success:
                migrated_count += 1
            else:
                print_colored(
                    f"Failed to migrate guild config {key} for guild {guild_id}",
                    Colors.RED,
                )

    print_colored(f"Migrated {migrated_count} guild configuration entries", Colors.GREEN)


async def migrate_user_infractions():
    """Migrate user infractions data."""
    print_colored("Migrating user infractions...", Colors.BLUE)

    infractions_path = "wdiscordbot-json-data/user_infractions.json"
    infractions_data = load_json_file(infractions_path)

    if not infractions_data:
        print_colored("No user infractions data to migrate", Colors.YELLOW)
        return

    migrated_count = 0
    for key, infractions_list in infractions_data.items():
        if not infractions_list:  # Skip empty lists
            continue

        # Parse the key format: "guild_id_user_id"
        try:
            guild_id_str, user_id_str = key.split("_", 1)
            guild_id = int(guild_id_str)
            user_id = int(user_id_str)
        except ValueError:
            print_colored(f"Invalid key format: {key}", Colors.RED)
            continue

        for infraction in infractions_list:
            try:
                timestamp_str = infraction.get("timestamp")
                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                else:
                    timestamp = datetime.now(timezone.utc)

                infraction_id = await add_user_infraction(
                    guild_id=guild_id,
                    user_id=user_id,
                    timestamp=timestamp,
                    rule_violated=infraction.get("rule_violated"),
                    action_taken=infraction.get("action_taken", "UNKNOWN"),
                    reasoning=infraction.get("reasoning"),
                )

                if infraction_id:
                    migrated_count += 1
                else:
                    print_colored(
                        f"Failed to migrate infraction for user {user_id} in guild {guild_id}",
                        Colors.RED,
                    )

            except Exception as e:
                print_colored(f"Error migrating infraction: {e}", Colors.RED)

    print_colored(f"Migrated {migrated_count} user infractions", Colors.GREEN)


async def migrate_appeals():
    """Migrate appeals data."""
    print_colored("Migrating appeals...", Colors.BLUE)

    appeals_path = "wdiscordbot-json-data/appeals.json"
    appeals_data = load_json_file(appeals_path)

    if not appeals_data:
        print_colored("No appeals data to migrate", Colors.YELLOW)
        return

    migrated_count = 0
    for appeal_id, appeal_data in appeals_data.items():
        try:
            # Create the appeal with the original ID
            timestamp_str = appeal_data.get("timestamp")
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                timestamp = datetime.now(timezone.utc)

            # Insert directly into database to preserve original appeal_id
            from database.connection import execute_query

            await execute_query(
                """INSERT INTO appeals (appeal_id, user_id, reason, timestamp, status, original_infraction)
                   VALUES ($1, $2, $3, $4, $5, $6)""",
                appeal_id,
                appeal_data.get("user_id"),
                appeal_data.get("reason", ""),
                timestamp,
                appeal_data.get("status", "pending"),
                json.dumps(appeal_data.get("original_infraction", {})),
            )

            migrated_count += 1

        except Exception as e:
            print_colored(f"Error migrating appeal {appeal_id}: {e}", Colors.RED)

    print_colored(f"Migrated {migrated_count} appeals", Colors.GREEN)


async def migrate_global_bans():
    """Migrate global bans data."""
    print_colored("Migrating global bans...", Colors.BLUE)

    bans_path = "wdiscordbot-json-data/global_bans.json"
    bans_data = load_json_file(bans_path)

    if not bans_data:
        print_colored("No global bans data to migrate", Colors.YELLOW)
        return

    migrated_count = 0
    for user_id in bans_data:
        try:
            success = await add_global_ban(int(user_id), reason="Migrated from JSON")
            if success:
                migrated_count += 1
            else:
                print_colored(f"Failed to migrate global ban for user {user_id}", Colors.RED)
        except Exception as e:
            print_colored(f"Error migrating global ban for user {user_id}: {e}", Colors.RED)

    print_colored(f"Migrated {migrated_count} global bans", Colors.GREEN)


async def migrate_logging_data():
    """Migrate logging system data."""
    print_colored("Migrating logging data...", Colors.BLUE)

    # Migrate moderation logs
    mod_logs_path = "logging-data/moderation_logs.json"
    mod_logs_data = load_json_file(mod_logs_path)

    migrated_mod_logs = 0
    if mod_logs_data:
        for log_entry in mod_logs_data:
            try:
                timestamp_str = log_entry.get("timestamp")
                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                else:
                    timestamp = datetime.now(timezone.utc)

                # Insert directly to preserve case_id if it exists
                from database.connection import execute_query

                if "case_id" in log_entry:
                    await execute_query(
                        """INSERT INTO moderation_logs 
                           (case_id, guild_id, moderator_id, target_user_id, action_type, reason, duration_seconds, timestamp, message_id, channel_id)
                           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
                        log_entry["case_id"],
                        log_entry.get("guild_id"),
                        log_entry.get("moderator_id"),
                        log_entry.get("target_user_id"),
                        log_entry.get("action_type", "UNKNOWN"),
                        log_entry.get("reason"),
                        log_entry.get("duration_seconds"),
                        timestamp,
                        log_entry.get("message_id"),
                        log_entry.get("channel_id"),
                    )
                else:
                    await add_mod_log(
                        guild_id=log_entry.get("guild_id"),
                        moderator_id=log_entry.get("moderator_id"),
                        target_user_id=log_entry.get("target_user_id"),
                        action_type=log_entry.get("action_type", "UNKNOWN"),
                        reason=log_entry.get("reason"),
                        duration_seconds=log_entry.get("duration_seconds"),
                    )

                migrated_mod_logs += 1

            except Exception as e:
                print_colored(f"Error migrating mod log: {e}", Colors.RED)

    # Migrate guild settings
    settings_path = "logging-data/guild_settings.json"
    settings_data = load_json_file(settings_path)

    migrated_settings = 0
    if settings_data:
        for guild_id_str, guild_settings in settings_data.items():
            guild_id = int(guild_id_str)
            for key, value in guild_settings.items():
                success = await set_guild_setting(guild_id, key, value)
                if success:
                    migrated_settings += 1

    # Migrate log event toggles
    toggles_path = "logging-data/log_event_toggles.json"
    toggles_data = load_json_file(toggles_path)

    migrated_toggles = 0
    if toggles_data:
        for guild_id_str, guild_toggles in toggles_data.items():
            guild_id = int(guild_id_str)
            for event_key, enabled in guild_toggles.items():
                success = await set_log_event_enabled(guild_id, event_key, enabled)
                if success:
                    migrated_toggles += 1

    print_colored(
        f"Migrated {migrated_mod_logs} moderation logs, {migrated_settings} guild settings, {migrated_toggles} log event toggles",
        Colors.GREEN,
    )


async def migrate_botdetect_config():
    """Migrate bot detection configuration."""
    print_colored("Migrating bot detection configuration...", Colors.BLUE)

    config_path = "wdiscordbot-json-data/botdetect_config.json"
    config_data = load_json_file(config_path)

    if not config_data:
        print_colored("No bot detection config data to migrate", Colors.YELLOW)
        return

    migrated_count = 0
    for guild_id_str, guild_config in config_data.items():
        guild_id = int(guild_id_str)

        for key, value in guild_config.items():
            success = await set_botdetect_config(guild_id, key, value)
            if success:
                migrated_count += 1
            else:
                print_colored(
                    f"Failed to migrate botdetect config {key} for guild {guild_id}",
                    Colors.RED,
                )

    print_colored(f"Migrated {migrated_count} bot detection configuration entries", Colors.GREEN)


async def migrate_user_data():
    """Migrate custom user data."""
    print_colored("Migrating custom user data...", Colors.BLUE)

    user_data_path = "user_data.json"
    user_data_content = load_json_file(user_data_path)

    if not user_data_content:
        print_colored("No custom user data to migrate", Colors.YELLOW)
        return

    migrated_count = 0
    for user_id_str, data in user_data_content.items():
        try:
            user_id = int(user_id_str)
            success = await set_user_data(user_id, data)
            if success:
                migrated_count += 1
            else:
                print_colored(f"Failed to migrate user data for user {user_id}", Colors.RED)
        except Exception as e:
            print_colored(f"Error migrating user data for user {user_id_str}: {e}", Colors.RED)

    print_colored(f"Migrated {migrated_count} custom user data entries", Colors.GREEN)


async def main():
    """Main migration function."""
    print_colored("=== JSON to PostgreSQL Migration Script ===", Colors.PURPLE)
    print_colored("This script will migrate all existing JSON data to PostgreSQL", Colors.CYAN)
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
        # Initialize database connection
        print_colored("Initializing database connection...", Colors.BLUE)
        await initialize_database()

        # Run migrations
        await migrate_guild_config()
        await migrate_user_infractions()
        await migrate_appeals()
        await migrate_global_bans()
        await migrate_logging_data()
        await migrate_botdetect_config()
        await migrate_user_data()

        print()
        print_colored("=== Migration Complete ===", Colors.GREEN)
        print_colored("All JSON data has been successfully migrated to PostgreSQL", Colors.GREEN)
        print_colored(
            "You can now update your bot code to use the PostgreSQL database",
            Colors.CYAN,
        )

    except Exception as e:
        print_colored(f"Migration failed: {e}", Colors.RED)
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
