import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Users, Server, Bot, Timer } from 'lucide-react';

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await axios.get('/api/stats');
        setStats(response.data);
      } catch (err) {
        setError('Failed to fetch stats.');
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

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
            value={stats.total_guilds}
            icon={Server}
          />
          <StatCard
            title="Total Users"
            value={stats.total_users}
            icon={Users}
          />
          <StatCard
            title="Commands Ran"
            value={stats.commands_ran}
            icon={Bot}
          />
          <StatCard title="Uptime" value={`${stats.uptime}%`} icon={Timer} />
        </div>
      </div>
      <div className="text-center text-muted-foreground">
        <p>Select a guild from the sidebar to view its configuration.</p>
      </div>
    </div>
  );
};

export default DashboardPage;
