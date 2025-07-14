import React, { useState, useEffect } from "react";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
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
import { Settings, Save, RefreshCw, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { FormDescription } from "./ui/form";

const GeneralSettings = ({ guildId }) => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      const response = await axios.get(
        `/api/guilds/${guildId}/config/general`
      );
      setConfig(response.data);
    } catch (error) {
      toast.error("Failed to load general settings");
      console.error("Error fetching general config:", error);
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

  const handleSave = async () => {
    try {
      setSaving(true);
      await axios.put(`/api/guilds/${guildId}/config/general`, config);
      toast.success("General settings saved successfully");
    } catch (error) {
      toast.error("Failed to save general settings");
      console.error("Error saving general config:", error);
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
          <Settings className="h-5 w-5" />
          General Settings
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <Label htmlFor="prefix">Command Prefix</Label>
            <Input
              id="prefix"
              value={config.prefix || "!"}
              onChange={(e) => handleInputChange("prefix", e.target.value)}
              placeholder="!"
            />
            <FormDescription>
              The prefix used to call bot commands.
            </FormDescription>
          </div>
          <div className="space-y-2">
            <Label htmlFor="language">Language</Label>
            <Select
              value={config.language || "en"}
              onValueChange={(value) => handleInputChange("language", value)}
            >
              <SelectTrigger id="language">
                <SelectValue placeholder="Select language" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="en">English</SelectItem>
                <SelectItem value="es">Spanish</SelectItem>
                <SelectItem value="fr">French</SelectItem>
              </SelectContent>
            </Select>
            <FormDescription>
              The language the bot will use for responses.
            </FormDescription>
          </div>
        </div>
        <div className="space-y-4">
          <div className="flex items-center justify-between rounded-lg border p-4">
            <div className="space-y-0.5">
              <Label htmlFor="bot-enabled" className="text-base">
                Bot Enabled
              </Label>
              <FormDescription>
                Enable or disable the bot completely in this server.
              </FormDescription>
            </div>
            <Switch
              id="bot-enabled"
              checked={config.bot_enabled || false}
              onCheckedChange={(value) =>
                handleInputChange("bot_enabled", value)
              }
            />
          </div>
          <div className="flex items-center justify-between rounded-lg border p-4">
            <div className="space-y-0.5">
              <Label htmlFor="test-mode" className="text-base">
                Test Mode
              </Label>
              <FormDescription>
                Enable test mode to restrict certain features to admins.
              </FormDescription>
            </div>
            <Switch
              id="test-mode"
              checked={config.test_mode || false}
              onCheckedChange={(value) => handleInputChange("test_mode", value)}
            />
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

export default GeneralSettings;