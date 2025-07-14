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
import { Badge } from "./ui/badge";
import {
  Zap,
  Save,
  RefreshCw,
  AlertTriangle,
  X,
  PlusCircle,
} from "lucide-react";
import { toast } from "sonner";
import { FormDescription } from "./ui/form";
import DiscordSelector from "./DiscordSelector";

const ChannelManagement = ({ guildId }) => {
  const [config, setConfig] = useState({
    nsfw_channels: [],
    suggestions_channel: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [newNsfwChannel, setNewNsfwChannel] = useState("");

  const fetchConfig = async () => {
    try {
      setLoading(true);
      const response = await axios.get(
        `/api/guilds/${guildId}/config/channels`
      );
      setConfig(response.data);
    } catch (error) {
      toast.error("Failed to load channel settings");
      console.error("Error fetching channel config:", error);
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
    setConfig((prev) => ({ ...prev, [field]: value }));
  };

  const handleAddNsfwChannel = () => {
    if (newNsfwChannel && !config.nsfw_channels.includes(newNsfwChannel)) {
      setConfig((prev) => ({
        ...prev,
        nsfw_channels: [...prev.nsfw_channels, newNsfwChannel],
      }));
      setNewNsfwChannel("");
    }
  };

  const handleRemoveNsfwChannel = (channelId) => {
    setConfig((prev) => ({
      ...prev,
      nsfw_channels: prev.nsfw_channels.filter((id) => id !== channelId),
    }));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await axios.put(`/api/guilds/${guildId}/config/channels`, config);
      toast.success("Channel settings saved successfully");
    } catch (error) {
      toast.error("Failed to save channel settings");
      console.error("Error saving channel config:", error);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (!config) {
    return (
      <div className="flex items-center justify-center h-64">
        <AlertTriangle className="h-8 w-8 text-red-500" />
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Zap className="h-5 w-5" />
          Channel Management
        </CardTitle>
        <CardDescription>
          Configure NSFW channels and other channel-specific settings.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-4">
          <h3 className="text-lg font-medium">NSFW Channels</h3>
          <FormDescription>
            Add Channel IDs that are designated as NSFW. The bot will allow
            NSFW content in these channels.
          </FormDescription>
          <div className="flex gap-2">
            <Input
              value={newNsfwChannel}
              onChange={(e) => setNewNsfwChannel(e.target.value)}
              placeholder="Enter Channel ID"
            />
            <Button onClick={handleAddNsfwChannel} size="icon">
              <PlusCircle className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {config.nsfw_channels?.map((channelId) => (
              <Badge key={channelId} variant="secondary">
                {channelId}
                <button
                  onClick={() => handleRemoveNsfwChannel(channelId)}
                  className="ml-2 rounded-full outline-none ring-offset-background focus:ring-2 focus:ring-ring focus:ring-offset-2"
                >
                  <X className="h-3 w-3 text-muted-foreground hover:text-foreground" />
                </button>
              </Badge>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <Label>Suggestions Channel</Label>
          <DiscordSelector
            guildId={guildId}
            type="channels"
            value={config.suggestions_channel}
            onValueChange={(value) =>
              handleInputChange("suggestions_channel", value)
            }
            placeholder="Select a channel..."
          />
          <FormDescription>
            Channel where user suggestions will be sent.
          </FormDescription>
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

export default ChannelManagement;