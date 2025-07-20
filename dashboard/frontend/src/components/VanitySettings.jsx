import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import DiscordSelector from "./DiscordSelector";
import { Link as LinkIcon, Save, RefreshCw, AlertTriangle } from "lucide-react";
import { toast } from "sonner";

const VanitySettings = ({ guildId }) => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchConfig = useCallback(async () => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/guilds/${guildId}/config/vanity`);
      setConfig(response.data);
    } catch (error) {
      toast.error("Failed to load vanity settings");
      console.error("Error fetching vanity config:", error);
    } finally {
      setLoading(false);
    }
  }, [guildId]);

  useEffect(() => {
    if (guildId) {
      fetchConfig();
    }
  }, [guildId, fetchConfig]);

  const handleInputChange = (field, value) => {
    setConfig((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await axios.put(`/api/guilds/${guildId}/config/vanity`, config);
      toast.success("Vanity settings saved successfully");
    } catch (error) {
      toast.error("Failed to save vanity settings");
      console.error("Error saving vanity config:", error);
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
          <LinkIcon className="h-5 w-5" />
          Vanity URL Settings
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="vanity_code">Vanity URL Code</Label>
          <Input
            id="vanity_code"
            value={config.lock_code ?? ""}
            onChange={(e) => handleInputChange("lock_code", e.target.value)}
            placeholder="coolvanity"
          />
        </div>
        <div className="space-y-2">
          <Label>Notification Channel</Label>
          <DiscordSelector
            guildId={guildId}
            type="channels"
            value={config.notify_channel_id ?? ""}
            onValueChange={(value) => handleInputChange("notify_channel_id", value)}
            placeholder="Select a channel..."
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="notify_target">Mention Role or Member ID</Label>
          <Input
            id="notify_target"
            value={config.notify_target_id ?? ""}
            onChange={(e) => handleInputChange("notify_target_id", e.target.value)}
            placeholder="Optional"
          />
        </div>
        <Button onClick={handleSave} disabled={saving} className="w-full">
          <Save className="h-4 w-4 mr-2" />
          {saving ? "Saving..." : "Save Vanity Settings"}
        </Button>
      </CardContent>
    </Card>
  );
};

export default VanitySettings;
