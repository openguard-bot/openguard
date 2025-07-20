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
import { Textarea } from "./ui/textarea";
import { Bot, Save, RefreshCw, AlertTriangle, Download } from "lucide-react";
import { toast } from "sonner";

const AISettings = ({ guildId }) => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

    const fetchConfig = useCallback(async () => {
      try {
        setLoading(true);
        const [aiRes, generalRes] = await Promise.all([
          axios.get(`/api/guilds/${guildId}/config/ai`),
          axios.get(`/api/guilds/${guildId}/config/general`),
        ]);
        setConfig({
          ...aiRes.data,
          ...generalRes.data,
          keyword_rules_raw: JSON.stringify(aiRes.data.keyword_rules || [], null, 2),
        });
      } catch (error) {
        toast.error("Failed to load AI settings");
        console.error("Error fetching AI config:", error);
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
      let rules = [];
      try {
        rules = JSON.parse(config.keyword_rules_raw || "[]");
      } catch {
        toast.error("Invalid keyword rules JSON");
        setSaving(false);
        return;
      }
      await Promise.all([
        axios.put(`/api/guilds/${guildId}/config/ai`, {
          channel_exclusions: config.channel_exclusions,
          channel_rules: config.channel_rules,
          analysis_mode: config.analysis_mode,
          keyword_rules: rules,
        }),
        axios.put(`/api/guilds/${guildId}/config/general`, {
          bot_enabled: config.bot_enabled,
          test_mode: config.test_mode,
        }),
      ]);
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
        <div className="space-y-4">
          <div className="flex items-center justify-between rounded-lg border p-4">
            <div className="space-y-0.5">
              <Label htmlFor="ai-moderation-enabled" className="text-base">
                AI Moderation Enabled
              </Label>
              <CardDescription>
                Toggle automated actions from the AI moderation system.
              </CardDescription>
            </div>
            <Switch
              id="ai-moderation-enabled"
              checked={config.bot_enabled || false}
              onCheckedChange={(value) => handleInputChange("bot_enabled", value)}
            />
          </div>
          <div className="flex items-center justify-between rounded-lg border p-4">
            <div className="space-y-0.5">
              <Label htmlFor="ai-test-mode" className="text-base">
                AI Test Mode
              </Label>
              <CardDescription>
                Analyze messages but require manual approval for actions.
              </CardDescription>
            </div>
            <Switch
              id="ai-test-mode"
              checked={config.test_mode || false}
              onCheckedChange={(value) => handleInputChange("test_mode", value)}
            />
          </div>
        </div>
            <div className="space-y-2">
              <Label htmlFor="analysis_mode">Analysis Mode</Label>
              <select
                id="analysis_mode"
                value={config.analysis_mode || "all"}
                onChange={(e) => handleInputChange("analysis_mode", e.target.value)}
                className="w-full border rounded p-2"
              >
                <option value="all">Analyze All Messages</option>
                <option value="rules_only">Only When Rules Match</option>
                <option value="override">Override With Rules</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="keyword_rules">Keyword/Regex Rules (JSON)</Label>
              <Textarea
                id="keyword_rules"
                value={config.keyword_rules_raw || "[]"}
                onChange={(e) => handleInputChange("keyword_rules_raw", e.target.value)}
                className="resize-y"
              />
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

export default AISettings;
