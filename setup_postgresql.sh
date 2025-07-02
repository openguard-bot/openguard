#!/bin/bash

# PostgreSQL Setup Script for Arch Linux
# This script installs and configures PostgreSQL for the Discord bot

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DB_NAME="aimod_bot"
DB_USER="aimod_user"
DB_PASSWORD="aimod_password_$(openssl rand -hex 8)"
POSTGRES_USER="postgres"

echo -e "${BLUE}=== PostgreSQL Setup for Discord Bot ===${NC}"
echo -e "${YELLOW}This script will install and configure PostgreSQL on Arch Linux${NC}"
echo

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}This script should not be run as root${NC}"
   echo -e "${YELLOW}Please run as a regular user with sudo privileges${NC}"
   exit 1
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if PostgreSQL is running
postgres_running() {
    systemctl is-active --quiet postgresql
}

# Function to check if database exists
database_exists() {
    sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$1"
}

# Function to check if user exists
user_exists() {
    sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$1'" | grep -q 1
}

echo -e "${BLUE}Step 1: Installing PostgreSQL${NC}"
if command_exists psql; then
    echo -e "${GREEN}PostgreSQL is already installed${NC}"
else
    echo -e "${YELLOW}Installing PostgreSQL...${NC}"
    sudo pacman -S --noconfirm postgresql
    echo -e "${GREEN}PostgreSQL installed successfully${NC}"
fi

echo -e "${BLUE}Step 2: Initializing PostgreSQL database cluster${NC}"
# Check if PostgreSQL data directory is already properly initialized
if sudo test -f "/var/lib/postgres/data/PG_VERSION"; then
    echo -e "${GREEN}PostgreSQL database cluster already initialized${NC}"
    PG_VERSION=$(sudo cat /var/lib/postgres/data/PG_VERSION)
    echo -e "${GREEN}PostgreSQL version: $PG_VERSION${NC}"
else
    # Check if data directory exists but is empty or corrupted
    if sudo test -d "/var/lib/postgres/data"; then
        if sudo test "$(sudo ls -A /var/lib/postgres/data 2>/dev/null | wc -l)" -gt 0; then
            echo -e "${YELLOW}Data directory exists but appears corrupted or incomplete${NC}"
            echo -e "${YELLOW}Backing up existing data directory...${NC}"
            sudo mv /var/lib/postgres/data /var/lib/postgres/data.backup.$(date +%Y%m%d_%H%M%S)
        fi
    fi

    echo -e "${YELLOW}Initializing database cluster...${NC}"
    sudo -u postgres initdb -D /var/lib/postgres/data
    echo -e "${GREEN}Database cluster initialized${NC}"
fi

echo -e "${BLUE}Step 3: Starting and enabling PostgreSQL service${NC}"

# Check if PostgreSQL service is running
if postgres_running; then
    echo -e "${GREEN}PostgreSQL is already running${NC}"
else
    echo -e "${YELLOW}Starting PostgreSQL service...${NC}"
    if sudo systemctl start postgresql; then
        echo -e "${GREEN}PostgreSQL service started successfully${NC}"
        # Wait a moment for the service to fully start
        sleep 2
    else
        echo -e "${RED}Failed to start PostgreSQL service${NC}"
        echo -e "${YELLOW}Checking service status...${NC}"
        sudo systemctl status postgresql --no-pager
        exit 1
    fi
fi

# Enable PostgreSQL to start on boot
echo -e "${YELLOW}Enabling PostgreSQL to start on boot...${NC}"
if sudo systemctl enable postgresql; then
    echo -e "${GREEN}PostgreSQL service enabled${NC}"
else
    echo -e "${YELLOW}PostgreSQL service may already be enabled${NC}"
fi

# Verify PostgreSQL is running after our changes
if postgres_running; then
    echo -e "${GREEN}PostgreSQL service is running and ready${NC}"
else
    echo -e "${RED}PostgreSQL service is not running - there may be an issue${NC}"
    sudo systemctl status postgresql --no-pager
    exit 1
fi

echo -e "${BLUE}Step 4: Creating database and user${NC}"

# Wait for PostgreSQL to be fully ready
echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
for i in {1..10}; do
    if sudo -u postgres psql -c "SELECT 1;" >/dev/null 2>&1; then
        echo -e "${GREEN}PostgreSQL is ready${NC}"
        break
    else
        echo -e "${YELLOW}Waiting for PostgreSQL... (attempt $i/10)${NC}"
        sleep 2
    fi
    if [ $i -eq 10 ]; then
        echo -e "${RED}PostgreSQL is not responding after 20 seconds${NC}"
        exit 1
    fi
done

# Create database user if it doesn't exist
if user_exists "$DB_USER"; then
    echo -e "${GREEN}User '$DB_USER' already exists${NC}"
    # Update password in case it changed
    echo -e "${YELLOW}Updating password for user '$DB_USER'...${NC}"
    sudo -u postgres psql -c "ALTER USER $DB_USER PASSWORD '$DB_PASSWORD';" >/dev/null 2>&1
else
    echo -e "${YELLOW}Creating database user '$DB_USER'...${NC}"
    if sudo -u postgres createuser --createdb --no-superuser --no-createrole "$DB_USER"; then
        sudo -u postgres psql -c "ALTER USER $DB_USER PASSWORD '$DB_PASSWORD';"
        echo -e "${GREEN}User '$DB_USER' created successfully${NC}"
    else
        echo -e "${RED}Failed to create user '$DB_USER'${NC}"
        exit 1
    fi
fi

# Create database if it doesn't exist
if database_exists "$DB_NAME"; then
    echo -e "${GREEN}Database '$DB_NAME' already exists${NC}"
    # Ensure the user owns the database
    echo -e "${YELLOW}Ensuring '$DB_USER' owns database '$DB_NAME'...${NC}"
    sudo -u postgres psql -c "ALTER DATABASE $DB_NAME OWNER TO $DB_USER;" >/dev/null 2>&1
else
    echo -e "${YELLOW}Creating database '$DB_NAME'...${NC}"
    if sudo -u postgres createdb -O "$DB_USER" "$DB_NAME"; then
        echo -e "${GREEN}Database '$DB_NAME' created successfully${NC}"
    else
        echo -e "${RED}Failed to create database '$DB_NAME'${NC}"
        exit 1
    fi
fi

echo -e "${BLUE}Step 5: Configuring PostgreSQL${NC}"

# Update postgresql.conf for better performance
POSTGRES_CONF="/var/lib/postgres/data/postgresql.conf"
echo -e "${YELLOW}Updating PostgreSQL configuration...${NC}"

# Backup original config
sudo cp "$POSTGRES_CONF" "$POSTGRES_CONF.backup.$(date +%Y%m%d_%H%M%S)"

# Update configuration settings
sudo -u postgres sed -i "s/#listen_addresses = 'localhost'/listen_addresses = 'localhost'/" "$POSTGRES_CONF"
sudo -u postgres sed -i "s/#port = 5432/port = 5432/" "$POSTGRES_CONF"
sudo -u postgres sed -i "s/#max_connections = 100/max_connections = 200/" "$POSTGRES_CONF"
sudo -u postgres sed -i "s/#shared_buffers = 128MB/shared_buffers = 256MB/" "$POSTGRES_CONF"
sudo -u postgres sed -i "s/#effective_cache_size = 4GB/effective_cache_size = 1GB/" "$POSTGRES_CONF"
sudo -u postgres sed -i "s/#maintenance_work_mem = 64MB/maintenance_work_mem = 128MB/" "$POSTGRES_CONF"
sudo -u postgres sed -i "s/#checkpoint_completion_target = 0.5/checkpoint_completion_target = 0.9/" "$POSTGRES_CONF"
sudo -u postgres sed -i "s/#wal_buffers = -1/wal_buffers = 16MB/" "$POSTGRES_CONF"
sudo -u postgres sed -i "s/#default_statistics_target = 100/default_statistics_target = 100/" "$POSTGRES_CONF"

echo -e "${GREEN}PostgreSQL configuration updated${NC}"

echo -e "${BLUE}Step 6: Restarting PostgreSQL to apply configuration${NC}"
sudo systemctl restart postgresql
echo -e "${GREEN}PostgreSQL restarted successfully${NC}"

echo -e "${BLUE}Step 7: Creating database schema${NC}"
echo -e "${YELLOW}Creating tables for the Discord bot...${NC}"

# Create the schema SQL
sudo -u postgres psql -d "$DB_NAME" << EOF
-- Guild configuration table
CREATE TABLE IF NOT EXISTS guild_config (
    guild_id BIGINT NOT NULL,
    key VARCHAR(255) NOT NULL,
    value JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, key)
);

-- User infractions table
CREATE TABLE IF NOT EXISTS user_infractions (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    rule_violated VARCHAR(50),
    action_taken VARCHAR(100),
    reasoning TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Appeals table
CREATE TABLE IF NOT EXISTS appeals (
    appeal_id UUID PRIMARY KEY,
    user_id BIGINT NOT NULL,
    reason TEXT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    original_infraction JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Global bans table
CREATE TABLE IF NOT EXISTS global_bans (
    id SERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL,
    reason TEXT,
    banned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    banned_by BIGINT
);

-- Moderation logs table
CREATE TABLE IF NOT EXISTS moderation_logs (
    case_id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    moderator_id BIGINT NOT NULL,
    target_user_id BIGINT NOT NULL,
    action_type VARCHAR(100) NOT NULL,
    reason TEXT,
    duration_seconds INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    message_id BIGINT,
    channel_id BIGINT
);

-- Guild settings table
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id BIGINT NOT NULL,
    key VARCHAR(255) NOT NULL,
    value JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, key)
);

-- Log event toggles table
CREATE TABLE IF NOT EXISTS log_event_toggles (
    guild_id BIGINT NOT NULL,
    event_key VARCHAR(255) NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, event_key)
);

-- Bot detection configuration table
CREATE TABLE IF NOT EXISTS botdetect_config (
    guild_id BIGINT NOT NULL,
    key VARCHAR(255) NOT NULL,
    value JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, key)
);

-- User data table (for abtuser.py)
CREATE TABLE IF NOT EXISTS user_data (
    user_id BIGINT PRIMARY KEY,
    data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_infractions_guild_user ON user_infractions(guild_id, user_id);
CREATE INDEX IF NOT EXISTS idx_user_infractions_timestamp ON user_infractions(timestamp);
CREATE INDEX IF NOT EXISTS idx_appeals_user_id ON appeals(user_id);
CREATE INDEX IF NOT EXISTS idx_appeals_status ON appeals(status);
CREATE INDEX IF NOT EXISTS idx_moderation_logs_guild_id ON moderation_logs(guild_id);
CREATE INDEX IF NOT EXISTS idx_moderation_logs_target_user ON moderation_logs(target_user_id);
CREATE INDEX IF NOT EXISTS idx_moderation_logs_timestamp ON moderation_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_guild_config_guild_id ON guild_config(guild_id);
CREATE INDEX IF NOT EXISTS idx_guild_settings_guild_id ON guild_settings(guild_id);
CREATE INDEX IF NOT EXISTS idx_log_event_toggles_guild_id ON log_event_toggles(guild_id);
CREATE INDEX IF NOT EXISTS idx_botdetect_config_guild_id ON botdetect_config(guild_id);

-- Grant permissions to the bot user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS \$\$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
\$\$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_guild_config_updated_at BEFORE UPDATE ON guild_config FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_appeals_updated_at BEFORE UPDATE ON appeals FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_guild_settings_updated_at BEFORE UPDATE ON guild_settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_log_event_toggles_updated_at BEFORE UPDATE ON log_event_toggles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_botdetect_config_updated_at BEFORE UPDATE ON botdetect_config FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_data_updated_at BEFORE UPDATE ON user_data FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

EOF

echo -e "${GREEN}Database schema created successfully${NC}"

echo -e "${BLUE}Step 8: Creating environment configuration${NC}"

# Create or update the database configuration in keys.env
ENV_FILE="keys.env"
if [ -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Updating $ENV_FILE with database configuration...${NC}"
    
    # Remove existing database configuration if present
    sed -i '/^DATABASE_URL=/d' "$ENV_FILE"
    sed -i '/^DB_HOST=/d' "$ENV_FILE"
    sed -i '/^DB_PORT=/d' "$ENV_FILE"
    sed -i '/^DB_NAME=/d' "$ENV_FILE"
    sed -i '/^DB_USER=/d' "$ENV_FILE"
    sed -i '/^DB_PASSWORD=/d' "$ENV_FILE"
    
    # Add new database configuration
    echo "" >> "$ENV_FILE"
    echo "# PostgreSQL Database Configuration" >> "$ENV_FILE"
    echo "DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME" >> "$ENV_FILE"
    echo "DB_HOST=localhost" >> "$ENV_FILE"
    echo "DB_PORT=5432" >> "$ENV_FILE"
    echo "DB_NAME=$DB_NAME" >> "$ENV_FILE"
    echo "DB_USER=$DB_USER" >> "$ENV_FILE"
    echo "DB_PASSWORD=$DB_PASSWORD" >> "$ENV_FILE"
    
    echo -e "${GREEN}Database configuration added to $ENV_FILE${NC}"
else
    echo -e "${YELLOW}Creating $ENV_FILE with database configuration...${NC}"
    cat > "$ENV_FILE" << EOF
# PostgreSQL Database Configuration
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME
DB_HOST=localhost
DB_PORT=5432
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
EOF
    echo -e "${GREEN}$ENV_FILE created with database configuration${NC}"
fi

echo
echo -e "${GREEN}=== PostgreSQL Setup Complete ===${NC}"
echo -e "${BLUE}Database Information:${NC}"
echo -e "  Database Name: ${GREEN}$DB_NAME${NC}"
echo -e "  Database User: ${GREEN}$DB_USER${NC}"
echo -e "  Database Password: ${GREEN}$DB_PASSWORD${NC}"
echo -e "  Connection URL: ${GREEN}postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME${NC}"
echo
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "1. Install Python PostgreSQL dependencies: ${BLUE}pip install asyncpg${NC}"
echo -e "2. Run the data migration script to transfer existing JSON data"
echo -e "3. Update your bot code to use PostgreSQL instead of JSON files"
echo
echo -e "${BLUE}To connect to the database manually:${NC}"
echo -e "  ${GREEN}psql -h localhost -U $DB_USER -d $DB_NAME${NC}"
echo
echo -e "${RED}Important: Save the database password securely!${NC}"
echo -e "${YELLOW}The password has been added to your keys.env file${NC}"
