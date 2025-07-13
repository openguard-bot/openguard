import React, { useState, useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import { Button } from "./ui/button";
import { ScrollArea } from "./ui/scroll-area";
import { RefreshCw } from "lucide-react";

const Sidebar = () => {
  const [guilds, setGuilds] = useState([]);
  const [error, setError] = useState(null);
  const { guildId } = useParams();
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchGuilds = async () => {
    try {
      const response = await axios.get("/api/guilds");
      setGuilds(response.data);
      setError(null);
    } catch (err) {
      setError(() => {
        if (err.response) {
          const data =
            typeof err.response.data === "string"
              ? err.response.data
              : JSON.stringify(err.response.data);
          return `Failed to fetch guilds. Error: ${data}`;
        } else {
          return `Failed to fetch guilds. Error: ${err.message}`;
        }
      });
      if (err.response && err.response.status === 401) {
        // Redirect to login if not authorized
        window.location.href = "/login";
      }
    }
  };

  useEffect(() => {
    fetchGuilds();
  }, []);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await axios.post("/api/guilds/refresh");
      await fetchGuilds();
    } catch (err) {
      setError("Failed to refresh guilds.");
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="flex min-h-screen w-64 flex-col border-r bg-background">
      <div className="flex items-center justify-between p-4">
        <h2 className="text-xl font-semibold">Your Guilds</h2>
        <Button
          onClick={handleRefresh}
          disabled={isRefreshing}
          variant="ghost"
          size="icon"
        >
          <RefreshCw
            className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`}
          />
        </Button>
      </div>
      <ScrollArea className="flex-1">
        <nav className="p-2">
          {error && <p className="p-2 text-red-500">{error}</p>}
          <ul>
            {guilds.map((guild) => (
              <li key={guild.id}>
                <Link
                  to={`/dashboard/${guild.id}`}
                  className={`flex items-center gap-2 rounded-md p-2 transition-colors hover:bg-muted ${
                    guildId === guild.id ? "bg-muted" : ""
                  }`}
                >
                  {guild.icon ? (
                    <img
                      src={`https://cdn.discordapp.com/icons/${guild.id}/${guild.icon}.png?size=32`}
                      alt={guild.name}
                      className="h-8 w-8 rounded-full"
                    />
                  ) : (
                    <div className="h-8 w-8 rounded-full bg-gray-700 flex items-center justify-center text-white text-sm font-bold">
                      {guild.name.charAt(0).toUpperCase()}
                    </div>
                  )}
                  <span className="truncate">{guild.name}</span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </ScrollArea>
      <div className="p-4">
        <Button asChild className="w-full">
          <a
            href={`https://discord.com/api/oauth2/authorize?client_id=${process.env.REACT_APP_DISCORD_CLIENT_ID}&permissions=8&scope=bot%20applications.commands`}
            target="_blank"
            rel="noopener noreferrer"
          >
            Add Server
          </a>
        </Button>
      </div>
    </div>
  );
};

export default Sidebar;
