import React, { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { ArrowRight, Settings, Zap, BarChart3, RefreshCw } from "lucide-react";

const GuildOverviewPage = () => {
  const { guildId } = useParams();
  const [guild, setGuild] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchGuild = useCallback(async () => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/guilds/${guildId}`);
      setGuild(response.data);
    } catch (error) { // Renamed 'err' to 'error'
      setError("Failed to fetch guild information.");
      console.error("Failed to fetch guild information:", error); // Log the error for debugging
    } finally {
      setLoading(false);
    }
  }, [guildId]);

  useEffect(() => {
    fetchGuild();
  }, [guildId, fetchGuild]); // Added fetchGuild to dependency array

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await axios.post("/api/guilds/refresh");
      await fetchGuild();
    } catch (error) { // Renamed 'err' to 'error'
      setError("Failed to refresh guild list.");
      console.error("Failed to refresh guild list:", error); // Log the error for debugging
    } finally {
      setIsRefreshing(false);
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>{error}</div>;
  }

  if (!guild) {
    return <div>Guild not found.</div>;
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-4">
        <img
          src={`https://cdn.discordapp.com/icons/${guild.id}/${guild.icon}.png?size=128`}
          alt={guild.name}
          className="h-24 w-24 rounded-full"
        />
        <div>
          <h2 className="text-3xl font-bold">{guild.name}</h2>
          <p className="text-muted-foreground">
            Configure your server settings and view statistics.
          </p>
        </div>
        <Button
          onClick={handleRefresh}
          disabled={isRefreshing}
          variant="outline"
          size="icon"
        >
          <RefreshCw
            className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`}
          />
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Server Configuration
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">
              Configure all bot features including AI moderation, security,
              logging, and more in one place.
            </p>
            <Button asChild className="mt-4">
              <Link to={`/${guildId}/config`}>
                Configure Server <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Analytics & Statistics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">
              View detailed analytics about your server's activity, command
              usage, and moderation statistics.
            </p>
            <Button asChild className="mt-4" variant="outline">
              <Link to={`/${guildId}/analytics`}>
                View Analytics <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default GuildOverviewPage;
