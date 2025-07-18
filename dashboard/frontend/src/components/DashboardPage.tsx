import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Users, Server, Bot, Timer } from 'lucide-react';

// for some reason eslint complains about icon not being used
const StatCard = ({ title, value, icon: Icon }) => (
  <Card>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium">{title}</CardTitle>
      <Icon className="h-4 w-4 text-muted-foreground" />
    </CardHeader>
    <CardContent>
      <div className="text-2xl font-bold">{value}</div>
    </CardContent>
  </Card>
);

const DashboardPage = () => {
  const [stats, setStats] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, healthRes] = await Promise.all([
          axios.get("/api/stats"),
          axios.get("/api/system/health"),
        ]);
        setStats(statsRes.data);
        setHealth(healthRes.data);
      } catch (err) {
        setError("Failed to fetch dashboard data.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const formatUptime = (seconds) => {
    if (seconds === 0) return "N/A";
    const d = Math.floor(seconds / (3600 * 24));
    const h = Math.floor((seconds % (3600 * 24)) / 3600);
    const m = Math.floor((seconds % 3600) / 60);

    const dDisplay = d > 0 ? d + (d === 1 ? " day, " : " days, ") : "";
    const hDisplay = h > 0 ? h + (h === 1 ? " hour, " : " hours, ") : "";
    const mDisplay = m > 0 ? m + (m === 1 ? " minute" : " minutes") : "";

    return (dDisplay + hDisplay + mDisplay).replace(/, $/, "");
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>{error}</div>;
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="mb-4 text-2xl font-semibold">Global Stats</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Total Guilds"
            value={stats?.total_guilds ?? "N/A"}
            icon={Server}
          />
          <StatCard
            title="Total Users"
            value={stats?.total_users ?? "N/A"}
            icon={Users}
          />
          <StatCard
            title="Commands Ran"
            value={stats?.commands_ran ?? "N/A"}
            icon={Bot}
          />
          <StatCard
            title="Uptime"
            value={health ? formatUptime(health.uptime_seconds) : "N/A"}
            icon={Timer}
          />
        </div>
      </div>
      <div className="text-center text-muted-foreground">
        <p>Select a guild from the sidebar to view its configuration.</p>
      </div>
    </div>
  );
};

export default DashboardPage;

