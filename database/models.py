"""
Database models and schema definitions for the Discord bot.
This module defines the structure of all database tables and provides
type hints for better code organization.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class AppealStatus(Enum):
    """Status options for appeals."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ActionType(Enum):
    """Moderation action types."""

    WARN = "WARN"
    TIMEOUT_SHORT = "TIMEOUT_SHORT"
    TIMEOUT_MEDIUM = "TIMEOUT_MEDIUM"
    TIMEOUT_LONG = "TIMEOUT_LONG"
    KICK = "KICK"
    BAN = "BAN"
    UNBAN = "UNBAN"
    MUTE = "MUTE"
    UNMUTE = "UNMUTE"


@dataclass
class GuildConfig:
    """Guild configuration model."""

    guild_id: int
    key: str
    value: Any
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class UserInfraction:
    """User infraction model."""

    id: Optional[int]
    guild_id: int
    user_id: int
    timestamp: datetime
    rule_violated: Optional[str]
    action_taken: str
    reasoning: Optional[str]
    created_at: Optional[datetime] = None


@dataclass
class Appeal:
    """Appeal model."""

    appeal_id: str
    user_id: int
    reason: str
    timestamp: datetime
    status: str = AppealStatus.PENDING.value
    original_infraction: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class GlobalBan:
    """Global ban model."""

    id: Optional[int]
    user_id: int
    reason: Optional[str]
    banned_at: Optional[datetime] = None
    banned_by: Optional[int] = None


@dataclass
class ModerationLog:
    """Moderation log model."""

    case_id: Optional[int]
    guild_id: int
    moderator_id: int
    target_user_id: int
    action_type: str
    reason: Optional[str]
    duration_seconds: Optional[int] = None
    timestamp: Optional[datetime] = None
    message_id: Optional[int] = None
    channel_id: Optional[int] = None


@dataclass
class GuildSetting:
    """Guild setting model."""

    guild_id: int
    key: str
    value: Any
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class LogEventToggle:
    """Log event toggle model."""

    guild_id: int
    event_key: str
    enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class BotDetectConfig:
    """Bot detection configuration model."""

    guild_id: int
    key: str
    value: Any
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class UserData:
    """User data model for custom user information."""

    user_id: int
    data: Dict[str, Any]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class GuildAPIKey:
    """Guild API Key model."""

    guild_id: int
    api_provider: Optional[str] = None
    api_key: Optional[str] = None
    github_auth_info: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class AIDecision:
    """AI moderation decision model."""

    id: Optional[int] = None
    guild_id: int = 0
    message_id: int = 0
    author_id: int = 0
    author_name: Optional[str] = None
    message_content_snippet: Optional[str] = None
    decision: Dict[str, Any] | None = None
    decision_timestamp: Optional[datetime] = None


@dataclass
class BlogPost:
    """Blog Post model."""

    id: Optional[int] = None
    title: str = ""
    content: str = ""
    author_id: int = 0
    published: bool = False
    slug: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class CaptchaConfig:
    """Captcha configuration model."""

    guild_id: int
    enabled: bool = False
    verification_role_id: Optional[int] = None
    max_attempts: int = 3
    fail_action: str = "kick"  # kick, ban, timeout
    timeout_duration: Optional[int] = None  # seconds for timeout action
    verification_channel_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class CaptchaAttempt:
    """Captcha attempt tracking model."""

    id: Optional[int] = None
    guild_id: int = 0
    user_id: int = 0
    attempt_count: int = 0
    last_attempt: Optional[datetime] = None
    verified: bool = False
    created_at: Optional[datetime] = None


# SQL Schema definitions for reference
SCHEMA_SQL = """
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

-- Command logs table
CREATE TABLE IF NOT EXISTS command_logs (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    command_name VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
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

-- Blog posts table
CREATE TABLE IF NOT EXISTS blog_posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    author_id BIGINT NOT NULL,
    published BOOLEAN DEFAULT false,
    slug VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Guild API Keys table
CREATE TABLE IF NOT EXISTS guild_api_keys (
    guild_id BIGINT PRIMARY KEY,
    api_provider VARCHAR(100),
    encrypted_api_key TEXT,
    encrypted_github_auth_info TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- AI moderation decisions table
CREATE TABLE IF NOT EXISTS ai_decisions (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    author_id BIGINT NOT NULL,
    author_name VARCHAR(255),
    message_content_snippet TEXT,
    decision JSONB,
    decision_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Captcha configuration table
CREATE TABLE IF NOT EXISTS captcha_config (
    guild_id BIGINT PRIMARY KEY,
    enabled BOOLEAN DEFAULT FALSE,
    verification_role_id BIGINT,
    max_attempts INTEGER DEFAULT 3,
    fail_action VARCHAR(50) DEFAULT 'kick',
    timeout_duration INTEGER,
    verification_channel_id BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Captcha attempts tracking table
CREATE TABLE IF NOT EXISTS captcha_attempts (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    attempt_count INTEGER DEFAULT 0,
    last_attempt TIMESTAMP WITH TIME ZONE,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, user_id)
);

-- Verification tokens table
CREATE TABLE IF NOT EXISTS verification_tokens (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, user_id)
);
"""

# Index creation SQL
INDEXES_SQL = """
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
CREATE INDEX IF NOT EXISTS idx_command_logs_guild_id ON command_logs(guild_id);
CREATE INDEX IF NOT EXISTS idx_command_logs_user_id ON command_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_command_logs_timestamp ON command_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_guild_api_keys_guild_id ON guild_api_keys(guild_id);
CREATE INDEX IF NOT EXISTS idx_blog_posts_author_id ON blog_posts(author_id);
CREATE INDEX IF NOT EXISTS idx_blog_posts_published ON blog_posts(published);
CREATE INDEX IF NOT EXISTS idx_blog_posts_slug ON blog_posts(slug);
CREATE INDEX IF NOT EXISTS idx_ai_decisions_guild_timestamp ON ai_decisions(guild_id, decision_timestamp);
"""

# Trigger creation SQL for automatic updated_at timestamps
TRIGGERS_SQL = """
-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_guild_config_updated_at BEFORE UPDATE ON guild_config FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_appeals_updated_at BEFORE UPDATE ON appeals FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_guild_settings_updated_at BEFORE UPDATE ON guild_settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_log_event_toggles_updated_at BEFORE UPDATE ON log_event_toggles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_botdetect_config_updated_at BEFORE UPDATE ON botdetect_config FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_data_updated_at BEFORE UPDATE ON user_data FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_guild_api_keys_updated_at BEFORE UPDATE ON guild_api_keys FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
"""
