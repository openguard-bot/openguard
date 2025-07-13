import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Switch } from "./ui/switch";
import { Textarea } from "./ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { Badge } from "./ui/badge";
import { Separator } from "./ui/separator";
import { toast } from "sonner";
import {
  Shield,
  MessageSquare,
  Users,
  FileText,
  Bot,
  Settings,
  Save,
  RefreshCw,
  AlertTriangle,
  Zap,
} from "lucide-react";

const GuildConfigPage = () => {
  const { guildId } = useParams();
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState("general");

  useEffect(() => {
    fetchConfig();
  }, [guildId]);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      const response = await axios.get(
        `/api/guilds/${guildId}/config/comprehensive`
      );
      setConfig(response.data);
    } catch (error) {
      toast.error("Failed to load configuration");
      console.error("Error fetching config:", error);
    } finally {
      setLoading(false);
    }
  };

  const updateConfig = async (section, data) => {
    try {
      setSaving(true);
      await axios.put(`/api/guilds/${guildId}/config/${section}`, data);
      toast.success("Configuration updated successfully");
      await fetchConfig(); // Refresh the config
    } catch (error) {
      toast.error("Failed to update configuration");
      console.error("Error updating config:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleInputChange = (section, field, value) => {
    setConfig((prev) => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value,
      },
    }));
  };

  const handleArrayChange = (section, field, index, value) => {
    setConfig((prev) => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: prev[section][field].map((item, i) =>
          i === index ? value : item
        ),
      },
    }));
  };

  const addArrayItem = (section, field, defaultValue = "") => {
    setConfig((prev) => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: [...prev[section][field], defaultValue],
      },
    }));
  };

  const removeArrayItem = (section, field, index) => {
    setConfig((prev) => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: prev[section][field].filter((_, i) => i !== index),
      },
    }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading configuration...</span>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="flex items-center justify-center h-64">
        <AlertTriangle className="h-8 w-8 text-red-500" />
        <span className="ml-2">Failed to load configuration</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Server Configuration</h1>
          <p className="text-muted-foreground">
            Configure all bot features and settings in one place
          </p>
        </div>
        <Button onClick={fetchConfig} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <Tabs
        value={activeTab}
        onValueChange={setActiveTab}
        className="space-y-4"
      >
        <TabsList className="grid w-full grid-cols-4 lg:grid-cols-8">
          <TabsTrigger value="general" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            General
          </TabsTrigger>
          <TabsTrigger value="ai" className="flex items-center gap-2">
            <Bot className="h-4 w-4" />
            AI & Moderation
          </TabsTrigger>
          <TabsTrigger value="security" className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            Security
          </TabsTrigger>
          <TabsTrigger value="logging" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Logging
          </TabsTrigger>
          <TabsTrigger value="message-rate" className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4" />
            Rate Limiting
          </TabsTrigger>
          <TabsTrigger value="raid-defense" className="flex items-center gap-2">
            <Users className="h-4 w-4" />
            Raid Defense
          </TabsTrigger>
          <TabsTrigger value="advanced" className="flex items-center gap-2">
            <Zap className="h-4 w-4" />
            Advanced
          </TabsTrigger>
        </TabsList>

        {/* General Settings Tab */}
        <TabsContent value="general">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                General Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="prefix">Command Prefix</Label>
                  <Input
                    id="prefix"
                    value={config.general?.prefix || "!"}
                    onChange={(e) =>
                      handleInputChange("general", "prefix", e.target.value)
                    }
                    placeholder="!"
                  />
                </div>
              </div>
              <Button
                onClick={() => updateConfig("general", config.general)}
                disabled={saving}
                className="w-full"
              >
                <Save className="h-4 w-4 mr-2" />
                Save General Settings
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* AI & Moderation Tab */}
        <TabsContent value="ai">
          <div className="space-y-6">
            {/* Moderation Settings */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  Moderation Configuration
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="mod_log_channel_id">
                      Mod Log Channel ID
                    </Label>
                    <Input
                      id="mod_log_channel_id"
                      value={config.moderation?.mod_log_channel_id || ""}
                      onChange={(e) =>
                        handleInputChange(
                          "moderation",
                          "mod_log_channel_id",
                          e.target.value
                        )
                      }
                      placeholder="Channel ID for moderation logs"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="moderator_role_id">Moderator Role ID</Label>
                    <Input
                      id="moderator_role_id"
                      value={config.moderation?.moderator_role_id || ""}
                      onChange={(e) =>
                        handleInputChange(
                          "moderation",
                          "moderator_role_id",
                          e.target.value
                        )
                      }
                      placeholder="Role ID for moderators"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="server_rules">Server Rules URL</Label>
                  <Input
                    id="server_rules"
                    value={config.moderation?.server_rules || ""}
                    onChange={(e) =>
                      handleInputChange(
                        "moderation",
                        "server_rules",
                        e.target.value
                      )
                    }
                    placeholder="https://example.com/rules"
                  />
                </div>
                <Button
                  onClick={() => updateConfig("moderation", config.moderation)}
                  disabled={saving}
                  className="w-full"
                >
                  <Save className="h-4 w-4 mr-2" />
                  Save Moderation Settings
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Security Tab */}
        <TabsContent value="security">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Bot Detection & Security
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center space-x-2">
                <Switch
                  id="bot_detection_enabled"
                  checked={config.bot_detection?.enabled || false}
                  onCheckedChange={(checked) =>
                    handleInputChange("bot_detection", "enabled", checked)
                  }
                />
                <Label htmlFor="bot_detection_enabled">
                  Enable Bot Detection
                </Label>
              </div>

              {config.bot_detection?.enabled && (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="bot_action">Action on Detection</Label>
                      <Select
                        value={config.bot_detection?.action || "warn"}
                        onValueChange={(value) =>
                          handleInputChange("bot_detection", "action", value)
                        }
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select action" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="warn">Warn</SelectItem>
                          <SelectItem value="kick">Kick</SelectItem>
                          <SelectItem value="ban">Ban</SelectItem>
                          <SelectItem value="timeout">Timeout</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="timeout_duration">
                        Timeout Duration (seconds)
                      </Label>
                      <Input
                        id="timeout_duration"
                        type="number"
                        value={config.bot_detection?.timeout_duration || 300}
                        onChange={(e) =>
                          handleInputChange(
                            "bot_detection",
                            "timeout_duration",
                            parseInt(e.target.value)
                          )
                        }
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Detection Keywords</Label>
                    <div className="space-y-2">
                      {config.bot_detection?.keywords?.map((keyword, index) => (
                        <div key={index} className="flex items-center gap-2">
                          <Input
                            value={keyword}
                            onChange={(e) =>
                              handleArrayChange(
                                "bot_detection",
                                "keywords",
                                index,
                                e.target.value
                              )
                            }
                            placeholder="Enter keyword"
                          />
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() =>
                              removeArrayItem(
                                "bot_detection",
                                "keywords",
                                index
                              )
                            }
                          >
                            Remove
                          </Button>
                        </div>
                      ))}
                      <Button
                        variant="outline"
                        onClick={() =>
                          addArrayItem("bot_detection", "keywords", "")
                        }
                      >
                        Add Keyword
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="log_channel">Log Channel ID</Label>
                    <Input
                      id="log_channel"
                      value={config.bot_detection?.log_channel || ""}
                      onChange={(e) =>
                        handleInputChange(
                          "bot_detection",
                          "log_channel",
                          e.target.value
                        )
                      }
                      placeholder="Channel ID for bot detection logs"
                    />
                  </div>
                </>
              )}

              <Button
                onClick={() =>
                  updateConfig("bot-detection", config.bot_detection)
                }
                disabled={saving}
                className="w-full"
              >
                <Save className="h-4 w-4 mr-2" />
                Save Security Settings
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Message Rate Limiting Tab */}
        <TabsContent value="message-rate">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                Message Rate Limiting
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center space-x-2">
                <Switch
                  id="rate_limiting_enabled"
                  checked={config.message_rate?.enabled || false}
                  onCheckedChange={(checked) =>
                    handleInputChange("message_rate", "enabled", checked)
                  }
                />
                <Label htmlFor="rate_limiting_enabled">
                  Enable Automatic Rate Limiting
                </Label>
              </div>

              {config.message_rate?.enabled && (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="high_rate_threshold">
                        High Rate Threshold
                      </Label>
                      <Input
                        id="high_rate_threshold"
                        type="number"
                        value={config.message_rate?.high_rate_threshold || 10}
                        onChange={(e) =>
                          handleInputChange(
                            "message_rate",
                            "high_rate_threshold",
                            parseInt(e.target.value)
                          )
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="low_rate_threshold">
                        Low Rate Threshold
                      </Label>
                      <Input
                        id="low_rate_threshold"
                        type="number"
                        value={config.message_rate?.low_rate_threshold || 3}
                        onChange={(e) =>
                          handleInputChange(
                            "message_rate",
                            "low_rate_threshold",
                            parseInt(e.target.value)
                          )
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="high_rate_slowmode">
                        High Rate Slowmode (s)
                      </Label>
                      <Input
                        id="high_rate_slowmode"
                        type="number"
                        value={config.message_rate?.high_rate_slowmode || 5}
                        onChange={(e) =>
                          handleInputChange(
                            "message_rate",
                            "high_rate_slowmode",
                            parseInt(e.target.value)
                          )
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="low_rate_slowmode">
                        Low Rate Slowmode (s)
                      </Label>
                      <Input
                        id="low_rate_slowmode"
                        type="number"
                        value={config.message_rate?.low_rate_slowmode || 2}
                        onChange={(e) =>
                          handleInputChange(
                            "message_rate",
                            "low_rate_slowmode",
                            parseInt(e.target.value)
                          )
                        }
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="check_interval">Check Interval (s)</Label>
                      <Input
                        id="check_interval"
                        type="number"
                        value={config.message_rate?.check_interval || 30}
                        onChange={(e) =>
                          handleInputChange(
                            "message_rate",
                            "check_interval",
                            parseInt(e.target.value)
                          )
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="analysis_window">
                        Analysis Window (s)
                      </Label>
                      <Input
                        id="analysis_window"
                        type="number"
                        value={config.message_rate?.analysis_window || 60}
                        onChange={(e) =>
                          handleInputChange(
                            "message_rate",
                            "analysis_window",
                            parseInt(e.target.value)
                          )
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="notification_channel">
                        Notification Channel ID
                      </Label>
                      <Input
                        id="notification_channel"
                        value={config.message_rate?.notification_channel || ""}
                        onChange={(e) =>
                          handleInputChange(
                            "message_rate",
                            "notification_channel",
                            e.target.value
                          )
                        }
                        placeholder="Optional"
                      />
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Switch
                      id="notifications_enabled"
                      checked={
                        config.message_rate?.notifications_enabled || true
                      }
                      onCheckedChange={(checked) =>
                        handleInputChange(
                          "message_rate",
                          "notifications_enabled",
                          checked
                        )
                      }
                    />
                    <Label htmlFor="notifications_enabled">
                      Enable Notifications
                    </Label>
                  </div>
                </>
              )}

              <Button
                onClick={() =>
                  updateConfig("message-rate", config.message_rate)
                }
                disabled={saving}
                className="w-full"
              >
                <Save className="h-4 w-4 mr-2" />
                Save Rate Limiting Settings
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Raid Defense Tab */}
        <TabsContent value="raid-defense">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                Raid Defense System
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center space-x-2">
                <Switch
                  id="raid_defense_enabled"
                  checked={config.raid_defense?.enabled || false}
                  onCheckedChange={(checked) =>
                    handleInputChange("raid_defense", "enabled", checked)
                  }
                />
                <Label htmlFor="raid_defense_enabled">
                  Enable Raid Defense
                </Label>
              </div>

              {config.raid_defense?.enabled && (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="raid_threshold">Join Threshold</Label>
                      <Input
                        id="raid_threshold"
                        type="number"
                        value={config.raid_defense?.threshold || 10}
                        onChange={(e) =>
                          handleInputChange(
                            "raid_defense",
                            "threshold",
                            parseInt(e.target.value)
                          )
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="raid_timeframe">
                        Timeframe (seconds)
                      </Label>
                      <Input
                        id="raid_timeframe"
                        type="number"
                        value={config.raid_defense?.timeframe || 60}
                        onChange={(e) =>
                          handleInputChange(
                            "raid_defense",
                            "timeframe",
                            parseInt(e.target.value)
                          )
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="alert_channel">Alert Channel ID</Label>
                      <Input
                        id="alert_channel"
                        value={config.raid_defense?.alert_channel || ""}
                        onChange={(e) =>
                          handleInputChange(
                            "raid_defense",
                            "alert_channel",
                            e.target.value
                          )
                        }
                        placeholder="Channel for raid alerts"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="auto_action">Automatic Action</Label>
                    <Select
                      value={config.raid_defense?.auto_action || "none"}
                      onValueChange={(value) =>
                        handleInputChange("raid_defense", "auto_action", value)
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select automatic action" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">None (Alert Only)</SelectItem>
                        <SelectItem value="lockdown">
                          Server Lockdown
                        </SelectItem>
                        <SelectItem value="kick_new">
                          Kick New Members
                        </SelectItem>
                        <SelectItem value="ban_new">Ban New Members</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </>
              )}

              <Button
                onClick={() =>
                  updateConfig("raid-defense", config.raid_defense)
                }
                disabled={saving}
                className="w-full"
              >
                <Save className="h-4 w-4 mr-2" />
                Save Raid Defense Settings
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Logging Tab */}
        <TabsContent value="logging">
          <div className="space-y-6">
            {/* Basic Logging */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Basic Logging
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="log_channel_id">Log Channel ID</Label>
                  <Input
                    id="log_channel_id"
                    value={config.logging?.log_channel_id || ""}
                    onChange={(e) =>
                      handleInputChange(
                        "logging",
                        "log_channel_id",
                        e.target.value
                      )
                    }
                    placeholder="Channel for general logs"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="message_delete_logging"
                      checked={config.logging?.message_delete_logging || false}
                      onCheckedChange={(checked) =>
                        handleInputChange(
                          "logging",
                          "message_delete_logging",
                          checked
                        )
                      }
                    />
                    <Label htmlFor="message_delete_logging">
                      Log Deleted Messages
                    </Label>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Switch
                      id="message_edit_logging"
                      checked={config.logging?.message_edit_logging || false}
                      onCheckedChange={(checked) =>
                        handleInputChange(
                          "logging",
                          "message_edit_logging",
                          checked
                        )
                      }
                    />
                    <Label htmlFor="message_edit_logging">
                      Log Edited Messages
                    </Label>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Switch
                      id="member_join_logging"
                      checked={config.logging?.member_join_logging || false}
                      onCheckedChange={(checked) =>
                        handleInputChange(
                          "logging",
                          "member_join_logging",
                          checked
                        )
                      }
                    />
                    <Label htmlFor="member_join_logging">
                      Log Member Joins
                    </Label>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Switch
                      id="member_leave_logging"
                      checked={config.logging?.member_leave_logging || false}
                      onCheckedChange={(checked) =>
                        handleInputChange(
                          "logging",
                          "member_leave_logging",
                          checked
                        )
                      }
                    />
                    <Label htmlFor="member_leave_logging">
                      Log Member Leaves
                    </Label>
                  </div>
                </div>

                <Button
                  onClick={() => updateConfig("logging", config.logging)}
                  disabled={saving}
                  className="w-full"
                >
                  <Save className="h-4 w-4 mr-2" />
                  Save Basic Logging Settings
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Advanced Tab */}
        <TabsContent value="advanced">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                Advanced Logging & Webhooks
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="webhook_url">Logging Webhook URL</Label>
                <Input
                  id="webhook_url"
                  value={config.advanced_logging?.webhook_url || ""}
                  onChange={(e) =>
                    handleInputChange(
                      "advanced_logging",
                      "webhook_url",
                      e.target.value
                    )
                  }
                  placeholder="https://discord.com/api/webhooks/..."
                  type="url"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="mod_log_enabled"
                    checked={config.advanced_logging?.mod_log_enabled || false}
                    onCheckedChange={(checked) =>
                      handleInputChange(
                        "advanced_logging",
                        "mod_log_enabled",
                        checked
                      )
                    }
                  />
                  <Label htmlFor="mod_log_enabled">
                    Enable Moderation Logging
                  </Label>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="mod_log_channel_id">Mod Log Channel ID</Label>
                  <Input
                    id="mod_log_channel_id"
                    value={config.advanced_logging?.mod_log_channel_id || ""}
                    onChange={(e) =>
                      handleInputChange(
                        "advanced_logging",
                        "mod_log_channel_id",
                        e.target.value
                      )
                    }
                    placeholder="Channel for moderation logs"
                  />
                </div>
              </div>

              <Separator />

              <div className="space-y-4">
                <h4 className="text-lg font-semibold">Event Logging Toggles</h4>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {config.advanced_logging?.event_toggles?.map(
                    (toggle, index) => (
                      <div
                        key={toggle.event_key}
                        className="flex items-center space-x-2"
                      >
                        <Switch
                          id={`event_${toggle.event_key}`}
                          checked={toggle.enabled}
                          onCheckedChange={(checked) => {
                            const newToggles = [
                              ...config.advanced_logging.event_toggles,
                            ];
                            newToggles[index] = { ...toggle, enabled: checked };
                            handleInputChange(
                              "advanced_logging",
                              "event_toggles",
                              newToggles
                            );
                          }}
                        />
                        <Label
                          htmlFor={`event_${toggle.event_key}`}
                          className="text-sm"
                        >
                          {toggle.event_key
                            .replace(/_/g, " ")
                            .replace(/\b\w/g, (l) => l.toUpperCase())}
                        </Label>
                      </div>
                    )
                  )}
                </div>
              </div>

              <Button
                onClick={() =>
                  updateConfig("advanced-logging", config.advanced_logging)
                }
                disabled={saving}
                className="w-full"
              >
                <Save className="h-4 w-4 mr-2" />
                Save Advanced Settings
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default GuildConfigPage;
