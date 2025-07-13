import React, { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import axios from "axios";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
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

const aiSettingsSchema = z.object({
  ai_enabled: z.boolean().default(false),
  ai_model: z.string().optional(),
  ai_temperature: z.number().min(0).max(1).optional(),
  ai_system_prompt: z.string().optional(),
});

const guildApiKeySchema = z.object({
  api_provider: z.string().min(1, "API Provider is required."),
  api_key: z.string().min(1, "API Key is required."),
});

const AISettings = ({ guildId }) => {
  const guildForm = useForm({
    resolver: zodResolver(aiSettingsSchema),
    defaultValues: {
      ai_enabled: false,
      ai_model: "",
      ai_temperature: 0.7,
      ai_system_prompt: "",
    },
  });

  const guildKeyForm = useForm({
    resolver: zodResolver(guildApiKeySchema),
    defaultValues: {
      api_provider: "",
      api_key: "",
    },
  });

  const [currentProvider, setCurrentProvider] = useState(null);

  useEffect(() => {
    const fetchGuildSettings = async () => {
      try {
        const response = await axios.get(`/api/guilds/${guildId}/config/ai`);
        guildForm.reset(response.data);
      } catch (error) {
        toast.error("Failed to fetch guild AI settings.");
      }
    };

    const fetchGuildKeyInfo = async () => {
      try {
        // Note: We don't fetch the key itself, just the provider info
        const response = await axios.get(`/api/guilds/${guildId}/api_key`);
        if (response.data && response.data.api_provider) {
          setCurrentProvider(response.data.api_provider);
        }
      } catch (error) {
        // It's okay if this fails, means guild has no key
      }
    };

    fetchGuildSettings();
    fetchGuildKeyInfo();
  }, [guildId, guildForm]);

  const onGuildSubmit = async (data) => {
    try {
      await axios.post(`/api/guilds/${guildId}/config/ai`, data);
      toast.success("Guild AI settings updated successfully.");
    } catch (error) {
      toast.error("Failed to update guild AI settings.");
    }
  };

  const onGuildKeySubmit = async (data) => {
    try {
      await axios.post(`/api/guilds/${guildId}/api_key`, data);
      setCurrentProvider(data.api_provider);
      guildKeyForm.reset({ api_provider: data.api_provider, api_key: "" }); // Clear key field
      toast.success("Guild API key has been saved.");
    } catch (error) {
      toast.error("Failed to save guild API key.");
    }
  };

  const onGuildKeyDelete = async () => {
    try {
      await axios.delete(`/api/guilds/${guildId}/api_key`);
      setCurrentProvider(null);
      guildKeyForm.reset({ api_provider: "", api_key: "" });
      toast.success("Guild API key has been deleted.");
    } catch (error) {
      toast.error("Failed to delete guild API key.");
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>AI Features Settings</CardTitle>
          <CardDescription>
            Configure the default AI-powered features for this guild.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...guildForm}>
            <form
              onSubmit={guildForm.handleSubmit(onGuildSubmit)}
              className="space-y-8"
            >
              <FormField
                control={guildForm.control}
                name="ai_enabled"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <FormLabel className="text-base">
                        Enable AI Features
                      </FormLabel>
                      <FormDescription>
                        Turn on or off AI-powered features for this guild.
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
                control={guildForm.control}
                name="ai_model"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Default AI Model</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="e.g., gpt-4-turbo, claude-3-opus-20240229"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      The default AI model for the guild (used if no custom key
                      is set).
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={guildForm.control}
                name="ai_temperature"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>AI Temperature</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        step="0.1"
                        min="0"
                        max="1"
                        placeholder="e.g., 0.7"
                        {...field}
                        onChange={(e) =>
                          field.onChange(parseFloat(e.target.value))
                        }
                      />
                    </FormControl>
                    <FormDescription>
                      Controls randomness (0.0-1.0). Higher is more creative.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={guildForm.control}
                name="ai_system_prompt"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>AI System Prompt</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="You are a helpful assistant."
                        className="resize-y"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      The default initial instructions or context for the AI.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button type="submit">Save Default Settings</Button>
            </form>
          </Form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Bring Your Own Key (BYOK)</CardTitle>
          <CardDescription>
            Use your guild's own LLM API key. This will override the default AI
            model settings. The key is write-only and encrypted at rest.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {currentProvider && (
            <div className="mb-4 p-4 bg-secondary rounded-md">
              <p className="text-sm font-medium">
                Current API Provider:{" "}
                <span className="font-bold text-primary">
                  {currentProvider}
                </span>
              </p>
              <p className="text-xs text-muted-foreground">
                To change the key, simply enter a new provider and key below and
                save.
              </p>
            </div>
          )}
          <Form {...guildKeyForm}>
            <form
              onSubmit={guildKeyForm.handleSubmit(onGuildKeySubmit)}
              className="space-y-8"
            >
              <FormField
                control={guildKeyForm.control}
                name="api_provider"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>AI Provider / Model</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="e.g., openai/gpt-4o, gemini/gemini-2.5-flash"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      The model you want to use from LiteLLM's provider list.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={guildKeyForm.control}
                name="api_key"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>API Key</FormLabel>
                    <FormControl>
                      <Input
                        type="password"
                        placeholder="Enter your key here"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      The guild's API key. It will not be shown again after
                      saving.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="flex space-x-2">
                <Button type="submit">Save Guild Key</Button>
                {currentProvider && (
                  <Button
                    type="button"
                    variant="destructive"
                    onClick={onGuildKeyDelete}
                  >
                    Delete Guild Key
                  </Button>
                )}
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
};

export default AISettings;
