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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { Shield, Save, RefreshCw, AlertTriangle } from "lucide-react";
import { toast } from "sonner";

const SecuritySettings = ({ guildId }) => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

    const fetchConfig = useCallback(async () => {
      try {
        setLoading(true);
        const response = await axios.get(
          `/api/guilds/${guildId}/config/bot-detection`
        );
        setConfig(response.data);
      } catch (error) {
        toast.error("Failed to load security settings");
        console.error("Error fetching security config:", error);
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

  const handleArrayChange = (field, index, value) => {
    setConfig((prev) => ({
      ...prev,
      [field]: prev[field].map((item, i) => (i === index ? value : item)),
    }));
  };

  const addArrayItem = (field, defaultValue = "") => {
    setConfig((prev) => ({
      ...prev,
      [field]: [...(prev[field] ?? []), defaultValue],
    }));
  };

  const removeArrayItem = (field, index) => {
    setConfig((prev) => ({
      ...prev,
      [field]: prev[field].filter((_, i) => i !== index),
    }));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await axios.put(
        `/api/guilds/${guildId}/config/bot-detection`,
        config
      );
      toast.success("Security settings saved successfully");
    } catch (error) {
      toast.error("Failed to save security settings");
      console.error("Error saving security config:", error);
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
          Bot Detection & Security
        </CardTitle>
        <CardDescription>
          Protect your server from malicious bots.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center space-x-2">
          <Switch
            id="bot_detection_enabled"
            checked={config.enabled ?? false}
            onCheckedChange={(checked) => handleSwitchChange("enabled", checked)}
          />
          <Label htmlFor="bot_detection_enabled">Enable Bot Detection</Label>
        </div>

        {config.enabled && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="bot_action">Action on Detection</Label>
                <Select
                  value={config.action ?? "warn"}
                  onValueChange={(value) => handleInputChange("action", value)}
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
                  value={config.timeout_duration ?? 300}
                  onChange={(e) =>
                    handleInputChange("timeout_duration", parseInt(e.target.value))
                  }
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Detection Keywords</Label>
              <div className="space-y-2">
                {(config.keywords ?? []).map((keyword, index) => (
                  <div key={index} className="flex items-center gap-2">
                    <Input
                      value={keyword}
                      onChange={(e) =>
                        handleArrayChange("keywords", index, e.target.value)
                      }
                      placeholder="Enter keyword"
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => removeArrayItem("keywords", index)}
                    >
                      Remove
                    </Button>
                  </div>
                ))}
                <Button
                  variant="outline"
                  onClick={() => addArrayItem("keywords", "")}
                >
                  Add Keyword
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="log_channel">Log Channel ID</Label>
              <Input
                id="log_channel"
                value={config.log_channel ?? ""}
                onChange={(e) =>
                  handleInputChange("log_channel", e.target.value)
                }
                placeholder="Channel ID for bot detection logs"
              />
            </div>
          </>
        )}

        <Button onClick={handleSave} disabled={saving} className="w-full">
          <Save className="h-4 w-4 mr-2" />
          {saving ? "Saving..." : "Save Security Settings"}
        </Button>
      </CardContent>
    </Card>
  );
};

export default SecuritySettings;