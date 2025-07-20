import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import axios from 'axios';
import { vi } from 'vitest';
import SecuritySettings from './SecuritySettings';
import { toast } from 'sonner';

vi.mock('axios');
vi.mock('sonner');

const mockConfig = {
  enabled: true,
  action: 'warn',
  timeout_duration: 300,
  keywords: ['spam'],
  log_channel: '123',
};

describe('SecuritySettings', () => {
  beforeEach(() => {
    axios.get.mockResolvedValue({ data: mockConfig });
    axios.put.mockResolvedValue({ data: {} });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', async () => {
    render(<SecuritySettings guildId="123" />);
    expect(screen.getByText(/Loading.../i)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText(/Loading.../i)).not.toBeInTheDocument());
  });

  it('renders settings form after loading', async () => {
    render(<SecuritySettings guildId="123" />);
    await waitFor(() => {
      expect(screen.getByLabelText(/Enable Bot Detection/i)).toBeChecked();
      expect(screen.getByLabelText(/Timeout Duration \(seconds\)/i)).toHaveValue(mockConfig.timeout_duration);
      expect(screen.getByLabelText(/Log Channel ID/i)).toHaveValue(mockConfig.log_channel);
    });
  });

  it('handles keyword add and remove', async () => {
    render(<SecuritySettings guildId="123" />);
    const addButton = await screen.findByRole('button', { name: /Add Keyword/i });

    fireEvent.click(addButton);
    const inputs = screen.getAllByPlaceholderText(/Enter keyword/i);
    expect(inputs).toHaveLength(2);

    fireEvent.change(inputs[1], { target: { value: 'bot' } });
    expect(inputs[1]).toHaveValue('bot');

    const removeButtons = screen.getAllByText(/Remove/i);
    fireEvent.click(removeButtons[1]);
    await waitFor(() => {
      expect(screen.getAllByPlaceholderText(/Enter keyword/i)).toHaveLength(1);
    });
  });

  it('saves settings and shows success toast', async () => {
    render(<SecuritySettings guildId="123" />);
    await waitFor(() => screen.getByText(/Save Security Settings/i));

    const saveButton = screen.getByText(/Save Security Settings/i);
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(axios.put).toHaveBeenCalledWith('/api/guilds/123/config/bot-detection', expect.any(Object));
      expect(toast.success).toHaveBeenCalledWith('Security settings saved successfully');
    });
  });

  it('shows an error message if fetching config fails', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    axios.get.mockRejectedValue(new Error('Fetch failed'));
    render(<SecuritySettings guildId="123" />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load settings/i)).toBeInTheDocument();
      expect(toast.error).toHaveBeenCalledWith('Failed to load security settings');
    });
    consoleErrorSpy.mockRestore();
  });
});
