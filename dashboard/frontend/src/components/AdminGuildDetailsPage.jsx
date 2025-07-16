import React, { useState, useEffect, useCallback } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { toast } from "sonner";
import AdminGuildSettings from "./AdminGuildSettings";

const AdminGuildDetailsPage = () => {
  const { guildId } = useParams();
  const [guild, setGuild] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchGuildDetails = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axios.get(`/api/admin/guilds/${guildId}`);
      setGuild(response.data);
    } catch (error) {
      console.error("Failed to fetch guild details:", error);
      toast.error("Failed to fetch guild details.");
    } finally {
      setLoading(false);
    }
  }, [guildId]);

  useEffect(() => {
    fetchGuildDetails();
  }, [fetchGuildDetails]);

  const handleRefresh = async () => {
    try {
      await axios.post(`/api/admin/guilds/${guildId}/refresh`);
      toast.success("Cache refreshed. Fetching latest data...");
      fetchGuildDetails();
    } catch (error) {
      console.error("Failed to refresh cache:", error);
      toast.error("Failed to refresh cache.");
    }
  };

  if (loading) {
    return <div>Loading guild details...</div>;
  }

  if (!guild) {
    return <div>Guild not found.</div>;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">
          {guild.name} ({guild.id})
        </h1>
        <Button onClick={handleRefresh}>Refresh Cache</Button>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Guild Information</CardTitle>
        </CardHeader>
        <CardContent>
          <p>
            <strong>Owner ID:</strong> {guild.owner_id}
          </p>
          <p>
            <strong>Members:</strong> {guild.member_count}
          </p>
        </CardContent>
      </Card>

      <AdminGuildSettings guildId={guildId} />
    </div>
  );
};

export default AdminGuildDetailsPage;