import React, { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import axios from "axios";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./ui/card";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "./ui/form";
import { RadioGroup, RadioGroupItem } from "./ui/radio-group";
import { toast } from "sonner";

const moderationSettingsSchema = z.object({
  mod_log_channel_id: z.string().optional().nullable(),
  moderator_role_id: z.string().optional().nullable(),
  server_rules: z.string().optional().nullable(),
  action_confirmation_settings: z.record(z.string()).optional(),
  confirmation_ping_role_id: z.string().optional().nullable(),
});

const ACTION_TYPES = ["BAN", "KICK", "MUTE", "WARN"];

const ModerationSettings = ({ guildId }) => {
  const form = useForm({
    resolver: zodResolver(moderationSettingsSchema),
    defaultValues: {
      mod_log_channel_id: "",
      moderator_role_id: "",
      server_rules: "",
      action_confirmation_settings: {},
      confirmation_ping_role_id: "",
    },
  });

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response = await axios.get(
          `/api/guilds/${guildId}/config/moderation`
        );
        const settings = response.data;
        // Ensure action_confirmation_settings is an object
        if (typeof settings.action_confirmation_settings === "string") {
          try {
            settings.action_confirmation_settings = JSON.parse(
              settings.action_confirmation_settings
            );
          } catch {
            settings.action_confirmation_settings = {}; // Fallback
          }
        }
        form.reset(settings);
      } catch (error) {
        toast.error("Failed to fetch moderation settings.");
      }
    };

    fetchSettings();
  }, [guildId, form]);

  const onSubmit = async (data) => {
    try {
      await axios.post(`/api/guilds/${guildId}/config/moderation`, data);
      toast.success("Moderation settings updated successfully.");
    } catch (error) {
      toast.error("Failed to update moderation settings.");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Moderation Settings</CardTitle>
        <CardDescription>
          Configure moderation features for your guild.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
            <FormField
              control={form.control}
              name="mod_log_channel_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Moderation Log Channel ID</FormLabel>
                  <FormControl>
                    <Input placeholder="Enter channel ID" {...field} />
                  </FormControl>
                  <FormDescription>
                    The channel where moderation actions will be logged.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="moderator_role_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Moderator Role ID</FormLabel>
                  <FormControl>
                    <Input placeholder="Enter role ID" {...field} />
                  </FormControl>
                  <FormDescription>
                    Users with this role can perform moderation actions.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="server_rules"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Server Rules</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Enter server rules URL or text"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    A link to your server rules or a brief description.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div>
              <h3 className="text-lg font-medium">Action Confirmation</h3>
              <p className="text-sm text-muted-foreground">
                Choose whether AI-driven actions require manual confirmation by
                a moderator.
              </p>
            </div>

            {ACTION_TYPES.map((action) => (
              <FormField
                key={action}
                control={form.control}
                name={`action_confirmation_settings.${action}`}
                render={({ field }) => (
                  <FormItem className="space-y-3">
                    <FormLabel>{action}</FormLabel>
                    <FormControl>
                      <RadioGroup
                        onValueChange={(value) => {
                          const currentSettings = form.getValues(
                            "action_confirmation_settings"
                          );
                          form.setValue("action_confirmation_settings", {
                            ...currentSettings,
                            [action]: value,
                          });
                        }}
                        value={field.value || "automatic"}
                        className="flex space-x-4"
                      >
                        <FormItem className="flex items-center space-x-2">
                          <FormControl>
                            <RadioGroupItem value="automatic" />
                          </FormControl>
                          <FormLabel className="font-normal">
                            Automatic
                          </FormLabel>
                        </FormItem>
                        <FormItem className="flex items-center space-x-2">
                          <FormControl>
                            <RadioGroupItem value="manual" />
                          </FormControl>
                          <FormLabel className="font-normal">Manual</FormLabel>
                        </FormItem>
                      </RadioGroup>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            ))}

            <FormField
              control={form.control}
              name="confirmation_ping_role_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Confirmation Ping Role ID</FormLabel>
                  <FormControl>
                    <Input placeholder="Enter role ID to ping" {...field} />
                  </FormControl>
                  <FormDescription>
                    The role to ping when an action requires manual
                    confirmation.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <Button type="submit">Save Changes</Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
};

export default ModerationSettings;
