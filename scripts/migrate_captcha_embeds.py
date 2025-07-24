#!/usr/bin/env python3
"""
Migration script to add captcha_embeds table for persistent verification embeds.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import initialize_database, execute_query


async def migrate_captcha_embeds():
    """Add the captcha_embeds table to the database."""
    print("Starting captcha embeds migration...")

    # Initialize database connection
    success = await initialize_database()
    if not success:
        print("Failed to initialize database connection")
        return False

    try:
        # Create the captcha_embeds table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS captcha_embeds (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            channel_id BIGINT NOT NULL,
            message_id BIGINT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(guild_id, channel_id, message_id)
        );
        """

        await execute_query(create_table_sql)
        print("✅ Successfully created captcha_embeds table")

        # Create index for better performance
        index_sql = """
        CREATE INDEX IF NOT EXISTS idx_captcha_embeds_active 
        ON captcha_embeds (guild_id, is_active);
        """

        await execute_query(index_sql)
        print("✅ Successfully created index on captcha_embeds table")

        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


async def main():
    """Run the migration."""
    success = await migrate_captcha_embeds()
    if success:
        print("🎉 Migration completed successfully!")
    else:
        print("💥 Migration failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
