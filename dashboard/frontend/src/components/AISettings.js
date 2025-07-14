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
import { Textarea } from "./ui/textarea";
import { Bot, Save, RefreshCw, AlertTriangle, Download } from "lucide-react";
import { toast } from "sonner";

const AISettings = ({ guildId }) => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/guilds/${guildId}/config/ai`);
      setConfig(response.data);
    } catch (error) {
      toast.error("Failed to load AI settings");
      console.error("Error fetching AI config:", error);
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

  const handleSwitchChange = (field, checked) => {
    setConfig((prev) => ({
      ...prev,
      [field]: checked,
    }));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await axios.put(`/api/guilds/${guildId}/config/ai`, config);
      toast.success("AI settings saved successfully");
    } catch (error) {
      toast.error("Failed to save AI settings");
      console.error("Error saving AI config:", error);
    } finally {
      setSaving(false);
    }
  };

  const handlePullRules = async () => {
    try {
      setIsSyncing(true);
      const response = await axios.post(
        `/api/guilds/${guildId}/config/ai/pull_rules`
      );
      toast.success("Rules synced successfully from #rules channel.");
      // Optionally, update a field in the config if the backend returns it
      if (response.data.ai_system_prompt) {
        handleInputChange("ai_system_prompt", response.data.ai_system_prompt);
      }
    } catch (error) {
      toast.error("Failed to sync rules.");
      console.error("Error pulling rules:", error);
    } finally {
      setIsSyncing(false);
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
          <Bot className="h-5 w-5" />
          AI Settings
        </CardTitle>
        <CardDescription>
          Configure AI-powered features for your server.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center space-x-2">
          <Switch
            id="ai_enabled"
            checked={config.ai_enabled || false}
            onCheckedChange={(checked) =>
              handleSwitchChange("ai_enabled", checked)
            }
          />
          <Label htmlFor="ai_enabled">Enable AI Features</Label>
        </div>

        {config.ai_enabled && (
          <>
            <div className="space-y-2">
              <Label htmlFor="ai_model">AI Model</Label>
              <Input
                id="ai_model"
                value={config.ai_model || ""}
                onChange={(e) => handleInputChange("ai_model", e.target.value)}
                placeholder="e.g., gpt-4-turbo"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ai_temperature">AI Temperature</Label>
              <Input
                id="ai_temperature"
                type="number"
                step="0.1"
                min="0"
                max="1"
                value={config.ai_temperature || 0.7}
                onChange={(e) =>
                  handleInputChange("ai_temperature", parseFloat(e.target.value))
                }
                placeholder="0.7"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ai_system_prompt">AI System Prompt</Label>
              <Textarea
                id="ai_system_prompt"
                value={config.ai_system_prompt || ""}
                onChange={(e) =>
                  handleInputChange("ai_system_prompt", e.target.value)
                }
                placeholder="You are a helpful assistant."
                className="resize-y"
              />
              <Button
                onClick={handlePullRules}
                disabled={isSyncing}
                variant="outline"
                className="w-full"
              >
                <Download className="h-4 w-4 mr-2" />
                {isSyncing ? "Syncing..." : "Sync Rules from #rules Channel"}
              </Button>
            </div>
          </>
        )}
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

export default AISettings;
