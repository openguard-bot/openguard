import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { 
  BarChart3, 
  Users, 
  MessageSquare, 
  Shield, 
  TrendingUp,
  Activity,
  Clock,
  AlertTriangle
} from 'lucide-react';

const AnalyticsDashboard = () => {
  const { guildId } = useParams();
  const [analytics, setAnalytics] = useState({
    commands: null,
    moderation: null,
    users: null,
    systemHealth: null
  });
  const [loading, setLoading] = useState(true);

  const fetchAnalytics = useCallback(async () => {
    try {
      setLoading(true);
      const [commandsRes, moderationRes, usersRes, healthRes] = await Promise.all([
        axios.get(`/api/analytics/commands?guild_id=${guildId}`),
        axios.get(`/api/analytics/moderation?guild_id=${guildId}`),
        axios.get(`/api/analytics/users?guild_id=${guildId}`),
        axios.get(`/api/system/health`)
      ]);
      
      setAnalytics({
        commands: commandsRes.data,
        moderation: moderationRes.data,
        users: usersRes.data,
        systemHealth: healthRes.data
      });
    } catch (error) {
      console.error('Error fetching analytics:', error);
    } finally {
      setLoading(false);
    }
  }, [guildId]); // Added guildId to dependency array of useCallback

  useEffect(() => {
    fetchAnalytics();
  }, [guildId, fetchAnalytics]); // Added fetchAnalytics to dependency array


  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Activity className="h-8 w-8 animate-pulse" />
        <span className="ml-2">Loading analytics...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Analytics Dashboard</h1>
          <p className="text-muted-foreground">
            Real-time insights into your server's activity and performance
          </p>
        </div>
      </div>

      {/* System Health */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            System Health
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {analytics.systemHealth?.uptime_percentage || 'N/A'}%
              </div>
              <div className="text-sm text-muted-foreground">Uptime</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">
                {analytics.systemHealth?.cpu_usage || 'N/A'}%
              </div>
              <div className="text-sm text-muted-foreground">CPU Usage</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">
                {analytics.systemHealth?.memory_usage || 'N/A'}%
              </div>
              <div className="text-sm text-muted-foreground">Memory Usage</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">
                {analytics.systemHealth?.active_connections || 'N/A'}
              </div>
              <div className="text-sm text-muted-foreground">Active Connections</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Command Analytics */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Command Usage
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold">
                    {analytics.commands?.total_commands || 0}
                  </div>
                  <div className="text-sm text-muted-foreground">Total Commands</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold">
                    {analytics.commands?.commands_today || 0}
                  </div>
                  <div className="text-sm text-muted-foreground">Today</div>
                </div>
              </div>
              
              {analytics.commands?.top_commands && (
                <div className="space-y-2">
                  <h4 className="font-semibold">Most Used Commands</h4>
                  {analytics.commands.top_commands.slice(0, 5).map((cmd, index) => (
                    <div key={index} className="flex justify-between items-center">
                      <span className="text-sm">{cmd.command_name}</span>
                      <Badge variant="secondary">{cmd.usage_count}</Badge>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Moderation Analytics */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Moderation Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold">
                    {analytics.moderation?.total_actions || 0}
                  </div>
                  <div className="text-sm text-muted-foreground">Total Actions</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold">
                    {analytics.moderation?.actions_today || 0}
                  </div>
                  <div className="text-sm text-muted-foreground">Today</div>
                </div>
              </div>
              
              {analytics.moderation?.action_breakdown && (
                <div className="space-y-2">
                  <h4 className="font-semibold">Action Breakdown</h4>
                  {Object.entries(analytics.moderation.action_breakdown).map(([action, count]) => (
                    <div key={action} className="flex justify-between items-center">
                      <span className="text-sm capitalize">{action}</span>
                      <Badge variant="outline">{count}</Badge>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* User Analytics */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              User Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold">
                    {analytics.users?.active_users || 0}
                  </div>
                  <div className="text-sm text-muted-foreground">Active Users</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold">
                    {analytics.users?.new_members_today || 0}
                  </div>
                  <div className="text-sm text-muted-foreground">New Today</div>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold">
                    {analytics.users?.messages_today || 0}
                  </div>
                  <div className="text-sm text-muted-foreground">Messages Today</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold">
                    {analytics.users?.average_online || 0}
                  </div>
                  <div className="text-sm text-muted-foreground">Avg Online</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {analytics.moderation?.recent_actions?.slice(0, 5).map((action, index) => (
                <div key={index} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-orange-500" />
                    <span>{action.action_type}</span>
                  </div>
                  <span className="text-muted-foreground">
                    {new Date(action.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              )) || (
                <div className="text-center text-muted-foreground">
                  No recent activity
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;
