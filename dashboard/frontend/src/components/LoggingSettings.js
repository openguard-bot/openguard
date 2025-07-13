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
import { Switch } from "./ui/switch";
import { toast } from "sonner";

const loggingSettingsSchema = z.object({
  log_channel_id: z.string().optional(),
  message_delete_logging: z.boolean().default(false),
  message_edit_logging: z.boolean().default(false),
  member_join_logging: z.boolean().default(false),
  member_leave_logging: z.boolean().default(false),
});

const LoggingSettings = ({ guildId }) => {
  const form = useForm({
    resolver: zodResolver(loggingSettingsSchema),
    defaultValues: {
      log_channel_id: "",
      message_delete_logging: false,
      message_edit_logging: false,
      member_join_logging: false,
      member_leave_logging: false,
    },
  });

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response = await axios.get(
          `/api/guilds/${guildId}/config/logging`
        );
        form.reset(response.data);
      } catch (error) {
        toast({
          title: "Error",
          description: "Failed to fetch logging settings.",
          variant: "destructive",
        });
      }
    };

    fetchSettings();
  }, [guildId, form]);

  const onSubmit = async (data) => {
    try {
      await axios.post(`/api/guilds/${guildId}/config/logging`, data);
      toast({
        title: "Success",
        description: "Logging settings updated successfully.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update logging settings.",
        variant: "destructive",
      });
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Logging Settings</CardTitle>
        <CardDescription>
          Configure logging features for your guild.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
            <FormField
              control={form.control}
              name="log_channel_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Log Channel ID</FormLabel>
                  <FormControl>
                    <Input placeholder="Enter channel ID" {...field} />
                  </FormControl>
                  <FormDescription>
                    The channel where various bot activities will be logged.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="message_delete_logging"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <FormLabel className="text-base">
                      Log Message Deletions
                    </FormLabel>
                    <FormDescription>
                      Enable logging of deleted messages.
                    </FormDescription>
                  </div>
                  <FormControl>
                    <Switch
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="message_edit_logging"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <FormLabel className="text-base">
                      Log Message Edits
                    </FormLabel>
                    <FormDescription>
                      Enable logging of edited messages.
                    </FormDescription>
                  </div>
                  <FormControl>
                    <Switch
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="member_join_logging"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <FormLabel className="text-base">
                      Log Member Joins
                    </FormLabel>
                    <FormDescription>
                      Enable logging when a new member joins the guild.
                    </FormDescription>
                  </div>
                  <FormControl>
                    <Switch
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="member_leave_logging"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <FormLabel className="text-base">
                      Log Member Leaves
                    </FormLabel>
                    <FormDescription>
                      Enable logging when a member leaves the guild.
                    </FormDescription>
                  </div>
                  <FormControl>
                    <Switch
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
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

export default LoggingSettings;
