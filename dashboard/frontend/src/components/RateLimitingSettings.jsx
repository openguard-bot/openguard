import React, { useState, useEffect, useCallback } from "react";
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
import { MessageSquare, Save, RefreshCw, AlertTriangle } from "lucide-react";
import { toast } from "sonner";

const RateLimitingSettings = ({ guildId }) => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

    const fetchConfig = useCallback(async () => {
      try {
        setLoading(true);
        const response = await axios.get(
          `/api/guilds/${guildId}/config/message-rate`
        );
        setConfig(response.data);
      } catch (error) {
        toast.error("Failed to load rate limiting settings");
        console.error("Error fetching rate limiting config:", error);
      } finally {
        setLoading(false);
      }
    }, [guildId]); // Added guildId to dependency array of useCallback
  
    useEffect(() => {
      if (guildId) {
        fetchConfig();
      }
    }, [guildId, fetchConfig]); // Added fetchConfig to dependency array

  const handleInputChange = (field, value) => {
    setConfig((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSwitchChange = (field, checked) => {
    setConfig((prev) => ({
      ...prev,
      [field]: checked,
    }));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await axios.put(
        `/api/guilds/${guildId}/config/message-rate`,
        config
      );
      toast.success("Rate limiting settings saved successfully");
    } catch (error) {
      toast.error("Failed to save rate limiting settings");
      console.error("Error saving rate limiting config:", error);
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
          <MessageSquare className="h-5 w-5" />
          Message Rate Limiting
        </CardTitle>
        <CardDescription>
          Automatically manage channel slowmode based on message activity.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center space-x-2">
          <Switch
            id="rate_limiting_enabled"
            checked={config.enabled || false}
            onCheckedChange={(checked) => handleSwitchChange("enabled", checked)}
          />
          <Label htmlFor="rate_limiting_enabled">
            Enable Automatic Rate Limiting
          </Label>
        </div>

        {config.enabled && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label htmlFor="high_rate_threshold">High Rate Threshold</Label>
                <Input
                  id="high_rate_threshold"
                  type="number"
                  value={config.high_rate_threshold || 10}
                  onChange={(e) =>
                    handleInputChange(
                      "high_rate_threshold",
                      parseInt(e.target.value)
                    )
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="low_rate_threshold">Low Rate Threshold</Label>
                <Input
                  id="low_rate_threshold"
                  type="number"
                  value={config.low_rate_threshold || 3}
                  onChange={(e) =>
                    handleInputChange(
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
                  value={config.high_rate_slowmode || 5}
                  onChange={(e) =>
                    handleInputChange(
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
                  value={config.low_rate_slowmode || 2}
                  onChange={(e) =>
                    handleInputChange(
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
                  value={config.check_interval || 30}
                  onChange={(e) =>
                    handleInputChange(
                      "check_interval",
                      parseInt(e.target.value)
                    )
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="analysis_window">Analysis Window (s)</Label>
                <Input
                  id="analysis_window"
                  type="number"
                  value={config.analysis_window || 60}
                  onChange={(e) =>
                    handleInputChange(
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
                  value={config.notification_channel || ""}
                  onChange={(e) =>
                    handleInputChange("notification_channel", e.target.value)
                  }
                  placeholder="Optional"
                />
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="notifications_enabled"
                checked={config.notifications_enabled ?? true}
                onCheckedChange={(checked) =>
                  handleSwitchChange("notifications_enabled", checked)
                }
              />
              <Label htmlFor="notifications_enabled">Enable Notifications</Label>
            </div>
          </>
        )}

        <Button onClick={handleSave} disabled={saving} className="w-full">
          <Save className="h-4 w-4 mr-2" />
          {saving ? "Saving..." : "Save Rate Limiting Settings"}
        </Button>
      </CardContent>
    </Card>
  );
};

export default RateLimitingSettings;