import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import axios from 'axios';
import AISettings from './AISettings';
import { toast } from 'sonner';

vi.mock('axios');
vi.mock('sonner');

const mockConfig = {
  ai_enabled: true,
  ai_model: 'gpt-4-turbo',
  ai_temperature: 0.7,
  ai_system_prompt: 'You are a helpful assistant.',
  analysis_mode: 'all',
  keyword_rules: [],
  bot_enabled: true,
  test_mode: false,
};

describe('AISettings', () => {
  beforeEach(() => {
    axios.get.mockResolvedValue({ data: mockConfig });
    axios.put.mockResolvedValue({ data: {} });
    axios.post.mockResolvedValue({ data: { ai_system_prompt: 'Synced rules' } });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', async () => {
    render(<AISettings guildId="123" />);
    expect(screen.getByText(/Loading.../i)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText(/Loading.../i)).not.toBeInTheDocument());
  });

  it('renders settings form after loading', async () => {
    render(<AISettings guildId="123" />);
    await waitFor(() => {
      expect(screen.getByLabelText(/AI Moderation Enabled/i)).toBeChecked();
      expect(screen.getByLabelText(/AI Test Mode/i)).not.toBeChecked();
      expect(screen.getByLabelText(/Enable AI Features/i)).toBeChecked();
      expect(screen.getByLabelText(/AI Model/i)).toHaveValue(mockConfig.ai_model);
      expect(screen.getByLabelText(/AI Temperature/i)).toHaveValue(mockConfig.ai_temperature);
      expect(screen.getByLabelText(/AI System Prompt/i)).toHaveValue(mockConfig.ai_system_prompt);
    });
  });

  it('toggles AI features section', async () => {
    render(<AISettings guildId="123" />);
    await waitFor(() => screen.getByLabelText(/Enable AI Features/i));

    const aiEnabledSwitch = screen.getByLabelText(/Enable AI Features/i);
    fireEvent.click(aiEnabledSwitch);

    await waitFor(() => {
      expect(screen.queryByLabelText(/AI Model/i)).not.toBeInTheDocument();
    });
  });

  it('handles input changes', async () => {
    render(<AISettings guildId="123" />);
    await waitFor(() => screen.getByLabelText(/AI Model/i));

    const modelInput = screen.getByLabelText(/AI Model/i);
    fireEvent.change(modelInput, { target: { value: 'new-model' } });
    expect(modelInput).toHaveValue('new-model');

    const testModeSwitch = screen.getByLabelText(/AI Test Mode/i);
    fireEvent.click(testModeSwitch);
    expect(testModeSwitch).toBeChecked();
  });

  it('allows adding a keyword rule', async () => {
    render(<AISettings guildId="123" />);
    await waitFor(() => screen.getByText(/Add Rule/i));

    const addButton = screen.getByText(/Add Rule/i);
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(screen.getAllByText(/Remove Rule/i).length).toBe(1);
    });
  });

  it('saves settings and shows success toast', async () => {
    render(<AISettings guildId="123" />);
    await waitFor(() => screen.getByText(/Save Changes/i));

    const saveButton = screen.getByText(/Save Changes/i);
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(axios.put).toHaveBeenCalledWith('/api/guilds/123/config/ai', expect.any(Object));
      expect(axios.put).toHaveBeenCalledWith('/api/guilds/123/config/general', expect.any(Object));
      expect(toast.success).toHaveBeenCalledWith('AI settings saved successfully');
    });
  });

  it('syncs rules and updates system prompt', async () => {
    render(<AISettings guildId="123" />);
    await waitFor(() => screen.getByText(/Sync Rules from #rules Channel/i));

    const syncButton = screen.getByText(/Sync Rules from #rules Channel/i);
    fireEvent.click(syncButton);

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith('/api/guilds/123/config/ai/pull_rules');
      expect(toast.success).toHaveBeenCalledWith('Rules synced successfully from #rules channel.');
      expect(screen.getByLabelText(/AI System Prompt/i)).toHaveValue('Synced rules');
    });
  });

  it('handles sync error and shows error toast', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    axios.post.mockRejectedValue(new Error('Sync failed'));
    render(<AISettings guildId="123" />);
    await waitFor(() => screen.getByText(/Sync Rules from #rules Channel/i));

    const syncButton = screen.getByText(/Sync Rules from #rules Channel/i);
    fireEvent.click(syncButton);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to sync rules.');
    });
    consoleErrorSpy.mockRestore();
  });
});