import React, { useState, useEffect } from "react";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Switch } from "./ui/switch";
import { Shield, Save, RefreshCw, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { FormDescription } from "./ui/form";
import DiscordSelector from "./DiscordSelector";

const ModerationSettings = ({ guildId }) => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      const response = await axios.get(
        `/api/guilds/${guildId}/config/moderation`
      );
      setConfig(response.data);
    } catch (error) {
      toast.error("Failed to load moderation settings");
      console.error("Error fetching moderation config:", error);
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
    setConfig((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleActionConfirmationChange = (action, value) => {
    setConfig((prev) => ({
      ...prev,
      action_confirmations: {
        ...prev.action_confirmations,
        [action]: value,
      },
    }));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await axios.put(`/api/guilds/${guildId}/config/moderation`, config);
      toast.success("Moderation settings saved successfully");
    } catch (error) {
      toast.error("Failed to save moderation settings");
      console.error("Error saving moderation config:", error);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading...</span>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="flex items-center justify-center h-64">
        <AlertTriangle className="h-8 w-8 text-red-500" />
        <span className="ml-2">Failed to load settings</span>
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5" />
          Moderation Settings
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-4">
          <h3 className="text-lg font-medium">Action Confirmations</h3>
          <FormDescription>
            Require a confirmation step before performing moderation actions.
          </FormDescription>
          <div className="space-y-4">
            {[
              { id: "warn", label: "Warn Confirmation" },
              { id: "timeout", label: "Timeout Confirmation" },
              { id: "kick", label: "Kick Confirmation" },
              { id: "ban", label: "Ban Confirmation" },
            ].map(({ id, label }) => (
              <div
                key={id}
                className="flex items-center justify-between rounded-lg border p-4"
              >
                <Label htmlFor={`${id}-confirmation`} className="text-base">
                  {label}
                </Label>
                <Switch
                  id={`${id}-confirmation`}
                  checked={config.action_confirmations?.[id] || false}
                  onCheckedChange={(value) =>
                    handleActionConfirmationChange(id, value)
                  }
                />
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <h3 className="text-lg font-medium">Role Settings</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Suicidal Content Ping Role</Label>
              <DiscordSelector
                guildId={guildId}
                type="roles"
                value={config.suicidal_content_ping_role_id}
                onValueChange={(value) =>
                  handleInputChange("suicidal_content_ping_role_id", value)
                }
                placeholder="Select a role..."
              />
            </div>
            <div className="space-y-2">
              <Label>Confirmation Ping Role</Label>
              <DiscordSelector
                guildId={guildId}
                type="roles"
                value={config.confirmation_ping_role_id}
                onValueChange={(value) =>
                  handleInputChange("confirmation_ping_role_id", value)
                }
                placeholder="Select a role..."
              />
            </div>
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

export default ModerationSettings;
