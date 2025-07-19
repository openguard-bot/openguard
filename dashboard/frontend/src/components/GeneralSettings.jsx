import React, { useState, useEffect, useCallback } from "react";
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
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { Form, FormDescription } from "./ui/form";

const GeneralSettings = ({ guildId }) => {
  const form = useForm();
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

    const fetchConfig = useCallback(async () => {
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
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSave)} className="space-y-6">
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
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={fetchConfig} disabled={loading}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Reset
              </Button>
              <Button type="submit" disabled={saving}>
                <Save className="h-4 w-4 mr-2" />
                {saving ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
};

export default GeneralSettings;