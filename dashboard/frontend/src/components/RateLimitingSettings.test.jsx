import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import axios from 'axios';
import { vi } from 'vitest';
import RateLimitingSettings from './RateLimitingSettings';
import { toast } from 'sonner';

vi.mock('axios');
vi.mock('sonner');

const mockConfig = {
  enabled: true,
  high_rate_threshold: 10,
  low_rate_threshold: 3,
  high_rate_slowmode: 5,
  low_rate_slowmode: 2,
  check_interval: 30,
  analysis_window: 60,
  notification_channel: '123',
  notifications_enabled: true,
};

describe('RateLimitingSettings', () => {
  beforeEach(() => {
    axios.get.mockResolvedValue({ data: mockConfig });
    axios.put.mockResolvedValue({ data: {} });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', async () => {
    render(<RateLimitingSettings guildId="123" />);
    expect(screen.getByText(/Loading.../i)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText(/Loading.../i)).not.toBeInTheDocument());
  });

  it('renders settings form after loading', async () => {
    render(<RateLimitingSettings guildId="123" />);
    await waitFor(() => {
      expect(screen.getByLabelText(/Enable Automatic Rate Limiting/i)).toBeChecked();
      expect(screen.getByLabelText(/High Rate Threshold/i)).toHaveValue(mockConfig.high_rate_threshold);
      expect(screen.getByLabelText(/Low Rate Threshold/i)).toHaveValue(mockConfig.low_rate_threshold);
      expect(screen.getByLabelText(/High Rate Slowmode \(s\)/i)).toHaveValue(mockConfig.high_rate_slowmode);
      expect(screen.getByLabelText(/Low Rate Slowmode \(s\)/i)).toHaveValue(mockConfig.low_rate_slowmode);
    });
  });

  it('handles input changes', async () => {
    render(<RateLimitingSettings guildId="123" />);
    await waitFor(() => screen.getByLabelText(/High Rate Threshold/i));

    const thresholdInput = screen.getByLabelText(/High Rate Threshold/i);
    fireEvent.change(thresholdInput, { target: { value: '20' } });
    expect(thresholdInput).toHaveValue(20);
  });

  it('saves settings and shows success toast', async () => {
    render(<RateLimitingSettings guildId="123" />);
    await waitFor(() => screen.getByText(/Save Rate Limiting Settings/i));

    const saveButton = screen.getByText(/Save Rate Limiting Settings/i);
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(axios.put).toHaveBeenCalledWith('/api/guilds/123/config/message-rate', expect.any(Object));
      expect(toast.success).toHaveBeenCalledWith('Rate limiting settings saved successfully');
    });
  });

  it('shows an error message if fetching config fails', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    axios.get.mockRejectedValue(new Error('Fetch failed'));
    render(<RateLimitingSettings guildId="123" />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load settings/i)).toBeInTheDocument();
      expect(toast.error).toHaveBeenCalledWith('Failed to load rate limiting settings');
    });
    consoleErrorSpy.mockRestore();
  });
});
