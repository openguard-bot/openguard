import React, { useState, useEffect } from "react";
import axios from "axios";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { RefreshCw, Shield, Save } from "lucide-react";
import { toast } from "sonner";

const AutoModSettings = ({ guildId }) => {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);

  const fetchRules = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`/api/guilds/${guildId}/automod/rules`);
      setRules(res.data);
    } catch (e) {
      toast.error("Failed to load automod rules");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (guildId) {
      fetchRules();
    }
  }, [guildId]);

  const handleCreate = async () => {
    try {
      setCreating(true);
      const aiRes = await axios.post(`/api/guilds/${guildId}/automod/ai-regex`, {
        description,
      });
      const regex = aiRes.data.regex;
      await axios.post(`/api/guilds/${guildId}/automod/rules`, {
        name: newName,
        event_type: 1,
        trigger: { type: 1, regex_patterns: [regex] },
        actions: [{ type: 1 }],
        enabled: true,
      });
      setNewName("");
      setDescription("");
      await fetchRules();
      toast.success("AutoMod rule created");
    } catch (e) {
      toast.error("Failed to create rule");
    } finally {
      setCreating(false);
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

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5" />
          AutoMod Rules
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Rule Name</Label>
          <Input value={newName} onChange={(e) => setNewName(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label>Rule Description</Label>
          <Input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe what to block"
          />
        </div>
        <Button onClick={handleCreate} disabled={creating} className="w-full">
          <Save className="h-4 w-4 mr-2" />
          {creating ? "Creating..." : "Create Rule with AI"}
        </Button>
        <div className="space-y-1">
          {rules.map((r) => (
            <div key={r.id} className="border p-2 rounded">
              {r.name}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

export default AutoModSettings;
