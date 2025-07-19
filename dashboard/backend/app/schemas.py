from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class Guild(BaseModel):
    id: str
    name: str
    icon: Optional[str] = None
    owner: Optional[bool] = None
    permissions: Optional[int] = None
    member_count: Optional[int] = None
    owner_id: Optional[str] = None


class User(BaseModel):
    id: str
    username: str
    discriminator: str
    avatar: Optional[str]

    model_config = ConfigDict(orm_mode=True)


class CommandLog(BaseModel):
    id: Optional[int] = None
    guild_id: str
    user_id: int
    command_name: str
    timestamp: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ModerationSettings(BaseModel):
    mod_log_channel_id: Optional[str] = Field(
        None, description="The channel ID for moderation logs."
    )
    moderator_role_id: Optional[str] = Field(
        None, description="The role ID for moderators."
    )
    server_rules: Optional[str] = Field(
        None, description="A URL or text for server rules."
    )
    action_confirmation_settings: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="A mapping of action types to confirmation modes ('automatic' or 'manual').",
    )
    confirmation_ping_role_id: Optional[str] = Field(
        None, description="The role ID to ping for manual confirmations."
    )

    model_config = ConfigDict(from_attributes=True)


class ModerationSettingsUpdate(BaseModel):
    mod_log_channel_id: Optional[str] = Field(
        None, description="The channel ID for moderation logs."
    )
    moderator_role_id: Optional[str] = Field(
        None, description="The role ID for moderators."
    )
    server_rules: Optional[str] = Field(
        None, description="A URL or text for server rules."
    )
    action_confirmation_settings: Optional[Dict[str, str]] = Field(
        None,
        description="A mapping of action types to confirmation modes ('automatic' or 'manual').",
    )
    confirmation_ping_role_id: Optional[str] = Field(
        None, description="The role ID to ping for manual confirmations."
    )

    model_config = ConfigDict(from_attributes=True)


class LoggingSettings(BaseModel):
    log_channel_id: Optional[str] = Field(
        None, description="The channel ID for general logs."
    )
    message_delete_logging: bool = Field(
        False, description="Enable logging of deleted messages."
    )
    message_edit_logging: bool = Field(
        False, description="Enable logging of edited messages."
    )
    member_join_logging: bool = Field(
        False, description="Enable logging when a new member joins."
    )
    member_leave_logging: bool = Field(
        False, description="Enable logging when a member leaves."
    )

    model_config = ConfigDict(from_attributes=True)


class LoggingSettingsUpdate(BaseModel):
    log_channel_id: Optional[str] = Field(
        None, description="The channel ID for general logs."
    )
    message_delete_logging: Optional[bool] = Field(
        None, description="Enable logging of deleted messages."
    )
    message_edit_logging: Optional[bool] = Field(
        None, description="Enable logging of edited messages."
    )
    member_join_logging: Optional[bool] = Field(
        None, description="Enable logging when a new member joins."
    )
    member_leave_logging: Optional[bool] = Field(
        None, description="Enable logging when a member leaves."
    )

    model_config = ConfigDict(from_attributes=True)


class ChannelExclusionSettings(BaseModel):
    excluded_channels: List[str] = Field(
        default_factory=list,
        description="List of channel IDs excluded from AI moderation.",
    )

    model_config = ConfigDict(from_attributes=True)


class ChannelRuleSettings(BaseModel):
    channel_id: str = Field(description="The channel ID for the custom rules.")
    rules: str = Field(description="Custom AI moderation rules for this channel.")

    model_config = ConfigDict(from_attributes=True)


class ChannelRulesUpdate(BaseModel):
    channel_rules: Dict[str, str] = Field(
        default_factory=dict,
        description="Dictionary mapping channel IDs to their custom rules.",
    )

    model_config = ConfigDict(from_attributes=True)


class GuildConfig(BaseModel):
    # This schema is dynamic, so we allow extra fields
    model_config = ConfigDict(extra="allow")


class GuildConfigUpdate(BaseModel):
    # This schema is dynamic, so we allow extra fields
    model_config = ConfigDict(extra="allow")


class GeneralSettings(BaseModel):
    prefix: str = Field(..., description="The command prefix for the bot.")

    model_config = ConfigDict(from_attributes=True)


class GeneralSettingsUpdate(BaseModel):
    prefix: Optional[str] = Field(None, description="The command prefix for the bot.")

    model_config = ConfigDict(from_attributes=True)


class Stats(BaseModel):
    total_guilds: int
    total_users: int
    commands_ran: int
    uptime: float


class GuildAPIKey(BaseModel):
    guild_id: str
    api_provider: Optional[str] = None
    # The 'api_key' and 'github_auth_info' are not included here
    # because we should not be sending them back to the client.

    model_config = ConfigDict(from_attributes=True)


class GuildAPIKeyUpdate(BaseModel):
    api_provider: str
    api_key: Optional[str] = None
    github_auth_info: Optional[Dict[str, Any]] = None


class CommandUsageData(BaseModel):
    command_name: str
    usage_count: int
    last_used: datetime


class DailyUsageData(BaseModel):
    date: str
    count: int


class CommandAnalytics(BaseModel):
    total_commands: int
    unique_commands: int
    top_commands: List[CommandUsageData]
    daily_usage: List[DailyUsageData]


class ModerationActionData(BaseModel):
    action_type: str
    count: int
    percentage: float


class TopModeratorData(BaseModel):
    moderator_id: str
    action_count: int


class ModerationAnalytics(BaseModel):
    total_actions: int
    actions_by_type: List[ModerationActionData]
    daily_actions: List[DailyUsageData]
    top_moderators: List[TopModeratorData]


class UserActivityData(BaseModel):
    date: str
    active_users: int
    new_users: int
    commands_used: int


class UserAnalytics(BaseModel):
    total_active_users: int
    new_users_today: int
    activity_timeline: List[UserActivityData]


class GuildUser(BaseModel):
    user_id: int
    username: str
    discriminator: str
    avatar: Optional[str]
    joined_at: Optional[datetime]
    roles: List[str]
    infraction_count: int
    last_active: Optional[datetime]


class UserInfraction(BaseModel):
    id: int
    guild_id: str
    user_id: int
    timestamp: datetime
    rule_violated: Optional[str]
    action_taken: str
    reasoning: Optional[str]
    moderator_id: Optional[int]
    moderator_name: Optional[str]


class Appeal(BaseModel):
    appeal_id: str
    user_id: int
    username: str
    reason: str
    timestamp: datetime
    status: str
    original_infraction: Optional[Dict[str, Any]]
    created_at: datetime


class UserProfile(BaseModel):
    user_id: int
    username: str
    discriminator: str
    avatar: Optional[str]
    total_infractions: int
    recent_infractions: List[UserInfraction]
    guild_join_date: Optional[datetime]
    last_active: Optional[datetime]
    roles: List[str]
    command_usage_count: int


class ModerationAction(BaseModel):
    target_user_id: int
    action_type: str
    reason: Optional[str]
    duration_seconds: Optional[int]


class BotDetectionSettings(BaseModel):
    enabled: bool
    keywords: List[str]
    action: str
    timeout_duration: int
    log_channel: Optional[str]
    whitelist_roles: List[str]
    whitelist_users: List[str]


class BotDetectionSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    keywords: Optional[List[str]] = None
    action: Optional[str] = None
    timeout_duration: Optional[int] = None
    log_channel: Optional[str] = None
    whitelist_roles: Optional[List[str]] = None
    whitelist_users: Optional[List[str]] = None


class RateLimitingSettings(BaseModel):
    enabled: bool
    high_rate_threshold: int
    low_rate_threshold: int
    high_rate_slowmode: int
    low_rate_slowmode: int
    check_interval: int
    analysis_window: int
    notifications_enabled: bool
    notification_channel: Optional[str]


class RateLimitingSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    high_rate_threshold: Optional[int] = None
    low_rate_threshold: Optional[int] = None
    high_rate_slowmode: Optional[int] = None
    low_rate_slowmode: Optional[int] = None
    check_interval: Optional[int] = None
    analysis_window: Optional[int] = None
    notifications_enabled: Optional[bool] = None
    notification_channel: Optional[str] = None


class SecuritySettings(BaseModel):
    bot_detection: BotDetectionSettings

    model_config = ConfigDict(from_attributes=True)


class SecuritySettingsUpdate(BaseModel):
    bot_detection: Optional[BotDetectionSettingsUpdate] = None

    model_config = ConfigDict(from_attributes=True)


class AISettings(BaseModel):
    channel_exclusions: ChannelExclusionSettings
    channel_rules: ChannelRulesUpdate

    model_config = ConfigDict(from_attributes=True)


class AISettingsUpdate(BaseModel):
    channel_exclusions: Optional[ChannelExclusionSettings] = None
    channel_rules: Optional[ChannelRulesUpdate] = None

    model_config = ConfigDict(from_attributes=True)


class ChannelsSettings(BaseModel):
    exclusions: List[str]
    rules: Dict[str, str]

    model_config = ConfigDict(from_attributes=True)


class ChannelsSettingsUpdate(BaseModel):
    exclusions: Optional[List[str]] = None
    rules: Optional[Dict[str, str]] = None

    model_config = ConfigDict(from_attributes=True)


class RaidDefenseSettings(BaseModel):
    enabled: bool
    threshold: int
    timeframe: int
    alert_channel: Optional[str]
    auto_action: str


class RaidDefenseSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    threshold: Optional[int] = None
    timeframe: Optional[int] = None
    alert_channel: Optional[str] = None
    auto_action: Optional[str] = None


class LogEventToggle(BaseModel):
    event_key: str
    enabled: bool


class AdvancedLoggingSettings(BaseModel):
    webhook_url: Optional[str]
    mod_log_enabled: bool
    mod_log_channel_id: Optional[str]
    event_toggles: List[LogEventToggle]


class AdvancedLoggingSettingsUpdate(BaseModel):
    webhook_url: Optional[str] = None
    mod_log_enabled: Optional[bool] = None
    mod_log_channel_id: Optional[str] = None
    event_toggles: Optional[List[LogEventToggle]] = None


class SystemHealth(BaseModel):
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    bot_status: str
    api_latency: int
    uptime_seconds: int


class AppealResponse(BaseModel):
    status: str
    reason: Optional[str]


class BlogPost(BaseModel):
    id: int
    title: str
    content: str
    author_id: int
    published: bool
    slug: str
    created_at: datetime
    updated_at: datetime
    tags: Optional[List[str]] = []

    model_config = ConfigDict(from_attributes=True)


class BlogPostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    published: bool = False
    slug: str = Field(..., min_length=1, max_length=255)


class BlogPostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, min_length=1)
    published: Optional[bool] = None
    slug: Optional[str] = Field(None, min_length=1, max_length=255)


class BlogPostList(BaseModel):
    posts: List[BlogPost]
    total: int
    page: int
    per_page: int


class DiscordRole(BaseModel):
    id: str
    name: str
    color: int
    position: int


class DiscordChannel(BaseModel):
    id: str
    name: str
    type: int
    position: int


class AdminMessage(BaseModel):
    content: str
    channel_id: Optional[str] = None
    user_id: Optional[str] = None


class RawTableRowUpdate(BaseModel):
    pk_values: Dict[str, Any]
    row_data: Dict[str, Any]


class RawTableRowDelete(BaseModel):
    pk_values: Dict[str, Any]
