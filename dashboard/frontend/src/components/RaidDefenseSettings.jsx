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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { Users, Save, RefreshCw, AlertTriangle } from "lucide-react";
import { toast } from "sonner";

const RaidDefenseSettings = ({ guildId }) => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      const response = await axios.get(
        `/api/guilds/${guildId}/config/raid-defense`
      );
      setConfig(response.data);
    } catch (error) {
      toast.error("Failed to load raid defense settings");
      console.error("Error fetching raid defense config:", error);
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
      await axios.put(
        `/api/guilds/${guildId}/config/raid-defense`,
        config
      );
      toast.success("Raid defense settings saved successfully");
    } catch (error) {
      toast.error("Failed to save raid defense settings");
      console.error("Error saving raid defense config:", error);
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
          <Users className="h-5 w-5" />
          Raid Defense System
        </CardTitle>
        <CardDescription>
          Configure automatic defenses against server raids.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center space-x-2">
          <Switch
            id="raid_defense_enabled"
            checked={config.enabled || false}
            onCheckedChange={(checked) => handleSwitchChange("enabled", checked)}
          />
          <Label htmlFor="raid_defense_enabled">Enable Raid Defense</Label>
        </div>

        {config.enabled && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="raid_threshold">Join Threshold</Label>
                <Input
                  id="raid_threshold"
                  type="number"
                  value={config.threshold || 10}
                  onChange={(e) =>
                    handleInputChange("threshold", parseInt(e.target.value))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="raid_timeframe">Timeframe (seconds)</Label>
                <Input
                  id="raid_timeframe"
                  type="number"
                  value={config.timeframe || 60}
                  onChange={(e) =>
                    handleInputChange("timeframe", parseInt(e.target.value))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="alert_channel">Alert Channel ID</Label>
                <Input
                  id="alert_channel"
                  value={config.alert_channel || ""}
                  onChange={(e) =>
                    handleInputChange("alert_channel", e.target.value)
                  }
                  placeholder="Channel for raid alerts"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="auto_action">Automatic Action</Label>
              <Select
                value={config.auto_action || "none"}
                onValueChange={(value) =>
                  handleInputChange("auto_action", value)
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select automatic action" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None (Alert Only)</SelectItem>
                  <SelectItem value="lockdown">Server Lockdown</SelectItem>
                  <SelectItem value="kick_new">Kick New Members</SelectItem>
                  <SelectItem value="ban_new">Ban New Members</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </>
        )}

        <Button onClick={handleSave} disabled={saving} className="w-full">
          <Save className="h-4 w-4 mr-2" />
          {saving ? "Saving..." : "Save Raid Defense Settings"}
        </Button>
      </CardContent>
    </Card>
  );
};

export default RaidDefenseSettings;