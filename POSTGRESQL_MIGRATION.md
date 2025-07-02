# PostgreSQL Migration Guide

This document describes the migration from JSON file storage to PostgreSQL database for the Discord bot.

## Overview

The bot has been migrated from using JSON files for data storage to using PostgreSQL database. This provides better performance, data integrity, concurrent access, and scalability.

## What Changed

### Data Storage Migration
- **Guild Configuration**: `wdiscordbot-json-data/guild_config.json` → `guild_config` table
- **User Infractions**: `wdiscordbot-json-data/user_infractions.json` → `user_infractions` table
- **Appeals**: `wdiscordbot-json-data/appeals.json` → `appeals` table
- **Global Bans**: `wdiscordbot-json-data/global_bans.json` → `global_bans` table
- **Moderation Logs**: `logging-data/moderation_logs.json` → `moderation_logs` table
- **Guild Settings**: `logging-data/guild_settings.json` → `guild_settings` table
- **Log Event Toggles**: `logging-data/log_event_toggles.json` → `log_event_toggles` table
- **Bot Detection Config**: `wdiscordbot-json-data/botdetect_config.json` → `botdetect_config` table
- **User Data**: `user_data.json` → `user_data` table

### Code Changes
- **Database Layer**: New `database/` module with PostgreSQL operations
- **Config Manager**: Updated to use async database calls
- **Logging Helpers**: Replaced JSON operations with PostgreSQL
- **Bot Detection**: Updated to use database storage
- **User Info**: Updated to use database storage
- **Bot Initialization**: Added database connection setup

## Migration Steps

### 1. Install PostgreSQL (Arch Linux)

Run the setup script:
```bash
./setup_postgresql.sh
```

This script will:
- Install PostgreSQL
- Initialize the database cluster
- Create the database and user
- Set up the schema with all required tables
- Configure environment variables

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

The new dependencies include:
- `asyncpg>=0.29.0,<1.0` - PostgreSQL async driver
- `psycopg2-binary>=2.9.0,<3.0` - PostgreSQL adapter (backup)

### 3. Migrate Existing Data

Run the migration script to transfer your existing JSON data:
```bash
./migrate_json_to_postgresql.py
```

This will:
- Read all existing JSON files
- Convert and insert data into PostgreSQL
- Preserve all existing data and relationships
- Handle data type conversions

### 4. Test the Migration

Run the test suite to verify everything works:
```bash
./test_postgresql_migration.py
```

This will test all database operations to ensure they work correctly.

### 5. Start the Bot

The bot will now automatically connect to PostgreSQL on startup:
```bash
python bot.py
```

## Database Schema

### Tables Created

1. **guild_config** - Guild-specific configuration settings
2. **user_infractions** - User infractions and violations
3. **appeals** - User appeals for infractions
4. **global_bans** - Globally banned users
5. **moderation_logs** - Moderation action logs
6. **guild_settings** - Logging system settings
7. **log_event_toggles** - Event logging toggles
8. **botdetect_config** - Bot detection configuration
9. **user_data** - Custom user data

### Key Features

- **JSONB Support**: Complex data structures stored as JSONB
- **Automatic Timestamps**: Created/updated timestamps with triggers
- **Indexes**: Optimized queries with proper indexing
- **Connection Pooling**: Efficient database connections
- **Transaction Support**: Data integrity with transactions

## Environment Variables

The following environment variables are required (automatically set by setup script):

```env
DATABASE_URL=postgresql://aimod_user:password@localhost:5432/aimod_bot
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aimod_bot
DB_USER=aimod_user
DB_PASSWORD=your_generated_password
```

## Backward Compatibility

### Legacy Support
- Old JSON files are preserved (not deleted)
- Legacy function signatures maintained where possible
- Gradual migration approach - both systems can coexist temporarily

### Breaking Changes
- Some functions are now async (marked in code)
- Direct JSON file access no longer works
- Configuration changes require database updates

## Performance Improvements

### Benefits of PostgreSQL
- **Concurrent Access**: Multiple bot instances can share data
- **ACID Compliance**: Data integrity guaranteed
- **Query Optimization**: Complex queries with indexes
- **Backup/Recovery**: Built-in backup and recovery tools
- **Scalability**: Handle larger datasets efficiently

### Connection Management
- **Connection Pooling**: Reuse database connections
- **Async Operations**: Non-blocking database calls
- **Error Handling**: Robust error handling and retries

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check PostgreSQL is running: `systemctl status postgresql`
   - Verify environment variables are set
   - Test connection: `psql -h localhost -U aimod_user -d aimod_bot`

2. **Migration Errors**
   - Ensure JSON files exist and are readable
   - Check database permissions
   - Review migration script output for specific errors

3. **Bot Startup Issues**
   - Check database initialization in bot logs
   - Verify all dependencies are installed
   - Ensure database schema is created

### Database Management

**Connect to Database:**
```bash
psql -h localhost -U aimod_user -d aimod_bot
```

**View Tables:**
```sql
\dt
```

**Check Data:**
```sql
SELECT COUNT(*) FROM guild_config;
SELECT COUNT(*) FROM user_infractions;
-- etc.
```

**Backup Database:**
```bash
pg_dump -h localhost -U aimod_user aimod_bot > backup.sql
```

**Restore Database:**
```bash
psql -h localhost -U aimod_user -d aimod_bot < backup.sql
```

## Rollback Plan

If you need to rollback to JSON files:

1. Stop the bot
2. Restore the original code from git
3. Ensure JSON files are in place
4. Restart the bot

Note: Any data created after migration will be lost in rollback.

## Monitoring

### Health Checks
- Database connection status in bot logs
- Query performance monitoring
- Error rate tracking

### Maintenance
- Regular database backups
- Index maintenance
- Connection pool monitoring
- Log rotation

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review bot logs for specific error messages
3. Test database connectivity manually
4. Run the test suite to identify specific problems

## Future Enhancements

Potential improvements with PostgreSQL:
- Advanced analytics and reporting
- Data archiving and retention policies
- Multi-guild data sharing
- Real-time data synchronization
- Advanced search capabilities
