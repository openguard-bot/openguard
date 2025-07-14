import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Switch } from "./ui/switch";
import { Separator } from "./ui/separator";
import { FileText, Save, RefreshCw, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { FormDescription } from "./ui/form";

const ALL_EVENT_KEYS = [
  "member_join",
  "member_remove",
  "member_ban_event",
  "member_unban",
  "member_update",
  "role_create_event",
  "role_delete_event",
  "role_update_event",
  "channel_create_event",
  "channel_delete_event",
  "channel_update_event",
  "message_edit",
  "message_delete",
  "reaction_add",
  "reaction_remove",
  "reaction_clear",
  "reaction_clear_emoji",
  "voice_state_update",
  "guild_update_event",
  "emoji_update_event",
  "invite_create_event",
  "invite_delete_event",
  "command_error",
  "thread_create",
  "thread_delete",
  "thread_update",
  "thread_member_join",
  "thread_member_remove",
  "webhook_update",
  "audit_kick",
  "audit_prune",
  "audit_ban",
  "audit_unban",
  "audit_member_role_update",
  "audit_member_update_timeout",
  "audit_message_delete",
  "audit_message_bulk_delete",
  "audit_role_create",
  "audit_role_delete",
  "audit_role_update",
  "audit_channel_create",
  "audit_channel_delete",
  "audit_channel_update",
  "audit_emoji_create",
  "audit_emoji_delete",
  "audit_emoji_update",
  "audit_invite_create",
  "audit_invite_delete",
  "audit_guild_update",
];

const LoggingSettings = ({ guildId }) => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      const response = await axios.get(
        `/api/guilds/${guildId}/config/logging`
      );
      setConfig(response.data);
    } catch (error) {
      toast.error("Failed to load logging settings");
      console.error("Error fetching logging config:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (guildId) {
      fetchConfig();
    }
  }, [guildId]);

  const handleInputChange = (field, value) => {
    setConfig((prev) => ({ ...prev, [field]: value }));
  };

  const handleEventToggle = (eventKey, enabled) => {
    setConfig((prev) => ({
      ...prev,
      enabled_events: {
        ...prev.enabled_events,
        [eventKey]: enabled,
      },
    }));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await axios.put(`/api/guilds/${guildId}/config/logging`, config);
      toast.success("Logging settings saved successfully");
    } catch (error) {
      toast.error("Failed to save logging settings");
      console.error("Error saving logging config:", error);
    } finally {
      setSaving(false);
    }
  };

  const formatEventKey = (key) => {
    return key
      .replace(/_/g, " ")
      .replace("event", "")
      .trim()
      .replace(/\b\w/g, (l) => l.toUpperCase());
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (!config) {
    return (
      <div className="flex items-center justify-center h-64">
        <AlertTriangle className="h-8 w-8 text-red-500" />
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Event Logging
        </CardTitle>
        <CardDescription>
          Configure detailed event logging using webhooks.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-2">
          <Label htmlFor="webhook_url">Logging Webhook URL</Label>
          <Input
            id="webhook_url"
            value={config.webhook_url || ""}
            onChange={(e) => handleInputChange("webhook_url", e.target.value)}
            placeholder="https://discord.com/api/webhooks/..."
            type="url"
          />
          <FormDescription>
            The webhook where all enabled log events will be sent.
          </FormDescription>
        </div>

        <Separator />

        <div className="space-y-4">
          <h3 className="text-lg font-medium">Event Toggles</h3>
          <FormDescription>
            Select which events you want to log.
          </FormDescription>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {ALL_EVENT_KEYS.map((key) => (
              <div key={key} className="flex items-center space-x-2">
                <Switch
                  id={key}
                  checked={config.enabled_events?.[key] ?? false}
                  onCheckedChange={(checked) => handleEventToggle(key, checked)}
                />
                <Label htmlFor={key} className="text-sm">
                  {formatEventKey(key)}
                </Label>
              </div>
            ))}
          </div>
        </div>

        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={fetchConfig} disabled={loading}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Reset
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            <Save className="h-4 w-4 mr-2" />
            {saving ? "Saving..." : "Save Changes"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default LoggingSettings;
