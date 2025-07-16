import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Switch } from "./ui/switch";
import { toast } from "sonner";

const AdminGuildSettings = ({ guildId }) => {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchSettings = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axios.get(`/api/admin/guilds/${guildId}/settings`);
      setSettings(response.data);
    } catch (error) {
      console.error("Failed to fetch guild settings:", error);
      toast.error("Failed to fetch guild settings.");
    } finally {
      setLoading(false);
    }
  }, [guildId]);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const handleInputChange = (key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    try {
      await axios.put(`/api/admin/guilds/${guildId}/settings`, settings);
      toast.success("Settings saved successfully.");
    } catch (error) {
      console.error("Failed to save guild settings:", error);
      toast.error("Failed to save guild settings.");
    }
  };

  const renderSettingInput = (key, value) => {
    if (typeof value === "boolean") {
      return (
        <div key={key} className="flex items-center space-x-2">
          <Switch
            id={key}
            checked={value}
            onCheckedChange={(checked) => handleInputChange(key, checked)}
          />
          <Label htmlFor={key} className="capitalize">
            {key.replace(/_/g, " ")}
          </Label>
        </div>
      );
    }

    if (typeof value === "number") {
      return (
        <div key={key} className="grid w-full max-w-sm items-center gap-1.5">
          <Label htmlFor={key} className="capitalize">
            {key.replace(/_/g, " ")}
          </Label>
          <Input
            type="number"
            id={key}
            value={value}
            onChange={(e) => handleInputChange(key, parseInt(e.target.value, 10))}
          />
        </div>
      );
    }

    return (
      <div key={key} className="grid w-full max-w-sm items-center gap-1.5">
        <Label htmlFor={key} className="capitalize">
          {key.replace(/_/g, " ")}
        </Label>
        <Input
          type="text"
          id={key}
          value={value || ""}
          onChange={(e) => handleInputChange(key, e.target.value)}
        />
      </div>
    );
  };

  if (loading) {
    return <div>Loading settings...</div>;
  }

  if (!settings) {
    return <div>Could not load settings.</div>;
  }

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle>Guild Settings</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {Object.entries(settings).map(([key, value]) =>
            renderSettingInput(key, value)
          )}
        </div>
        <Button onClick={handleSave} className="mt-4">
          Save Settings
        </Button>
      </CardContent>
    </Card>
  );
};

export default AdminGuildSettings;