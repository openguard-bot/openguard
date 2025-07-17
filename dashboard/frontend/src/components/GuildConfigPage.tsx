import React, { useState, useEffect } from "react";
import { useParams } from "react-router";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import {
  Shield,
  MessageSquare,
  Users,
  FileText,
  Bot,
  Settings,
  Zap,
} from "lucide-react";
import GeneralSettings from "./GeneralSettings";
import ModerationSettings from "./ModerationSettings";
import AISettings from "./AISettings";
import SecuritySettings from "./SecuritySettings";
import RaidDefenseSettings from "./RaidDefenseSettings";
import RateLimitingSettings from "./RateLimitingSettings";
import LoggingSettings from "./LoggingSettings";
import ChannelManagement from "./ChannelManagement";

const GuildConfigPage = () => {
  const { guildId } = useParams();
  const [activeTab, setActiveTab] = useState("general");

  useEffect(() => {
    console.log("GuildConfigPage - guildId:", guildId);
    console.log("GuildConfigPage - activeTab:", activeTab);
  }, [guildId, activeTab]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Server Configuration</h1>
          <p className="text-muted-foreground">
            Configure all bot features and settings in one place
          </p>
        </div>
      </div>

      <Tabs
        value={activeTab}
        onValueChange={setActiveTab}
        className="space-y-4"
      >
        <TabsList className="grid w-full grid-cols-4 lg:grid-cols-8">
          <TabsTrigger value="general" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            General
          </TabsTrigger>
          <TabsTrigger value="moderation" className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            Moderation
          </TabsTrigger>
          <TabsTrigger value="ai" className="flex items-center gap-2">
            <Bot className="h-4 w-4" />
            AI
          </TabsTrigger>
          <TabsTrigger value="security" className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            Security
          </TabsTrigger>
          <TabsTrigger value="raid-defense" className="flex items-center gap-2">
            <Users className="h-4 w-4" />
            Raid Defense
          </TabsTrigger>
          <TabsTrigger value="rate-limiting" className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4" />
            Rate Limiting
          </TabsTrigger>
          <TabsTrigger value="logging" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Logging
          </TabsTrigger>
          <TabsTrigger value="channels" className="flex items-center gap-2">
            <Zap className="h-4 w-4" />
            Channels
          </TabsTrigger>
        </TabsList>

        <TabsContent value="general">
          <GeneralSettings guildId={guildId} />
        </TabsContent>
        <TabsContent value="moderation">
          <ModerationSettings guildId={guildId} />
        </TabsContent>
        <TabsContent value="ai">
          <AISettings guildId={guildId} />
        </TabsContent>
        <TabsContent value="security">
          <SecuritySettings guildId={guildId} />
        </TabsContent>
        <TabsContent value="raid-defense">
          <RaidDefenseSettings guildId={guildId} />
        </TabsContent>
        <TabsContent value="rate-limiting">
          <RateLimitingSettings guildId={guildId} />
        </TabsContent>
        <TabsContent value="logging">
          <LoggingSettings guildId={guildId} />
        </TabsContent>
        <TabsContent value="channels">
          <ChannelManagement guildId={guildId} />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default GuildConfigPage;
