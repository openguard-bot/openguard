import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import axios from 'axios';
import { vi } from 'vitest';
import RaidDefenseSettings from './RaidDefenseSettings';
import { toast } from 'sonner';

vi.mock('axios');
vi.mock('sonner');

const mockConfig = {
  enabled: true,
  threshold: 5,
  timeframe: 60,
  alert_channel: '123',
  auto_action: 'none',
};

describe('RaidDefenseSettings', () => {
  beforeEach(() => {
    axios.get.mockResolvedValue({ data: mockConfig });
    axios.put.mockResolvedValue({ data: {} });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', async () => {
    render(<RaidDefenseSettings guildId="123" />);
    expect(screen.getByText(/Loading.../i)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText(/Loading.../i)).not.toBeInTheDocument());
  });

  it('renders settings form after loading', async () => {
    render(<RaidDefenseSettings guildId="123" />);
    await waitFor(() => {
      expect(screen.getByLabelText(/Enable Raid Defense/i)).toBeChecked();
      expect(screen.getByLabelText(/Join Threshold/i)).toHaveValue(mockConfig.threshold);
      expect(screen.getByLabelText(/Timeframe \(seconds\)/i)).toHaveValue(mockConfig.timeframe);
      expect(screen.getByLabelText(/Alert Channel ID/i)).toHaveValue(mockConfig.alert_channel);
    });
  });

  it('handles input changes', async () => {
    render(<RaidDefenseSettings guildId="123" />);
    await waitFor(() => screen.getByLabelText(/Join Threshold/i));

    const thresholdInput = screen.getByLabelText(/Join Threshold/i);
    fireEvent.change(thresholdInput, { target: { value: '10' } });
    expect(thresholdInput).toHaveValue(10);
  });

  it('saves settings and shows success toast', async () => {
    render(<RaidDefenseSettings guildId="123" />);
    await waitFor(() => screen.getByText(/Save Raid Defense Settings/i));

    const saveButton = screen.getByText(/Save Raid Defense Settings/i);
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(axios.put).toHaveBeenCalledWith('/api/guilds/123/config/raid-defense', expect.any(Object));
      expect(toast.success).toHaveBeenCalledWith('Raid defense settings saved successfully');
    });
  });

  it('shows an error message if fetching config fails', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    axios.get.mockRejectedValue(new Error('Fetch failed'));
    render(<RaidDefenseSettings guildId="123" />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load settings/i)).toBeInTheDocument();
      expect(toast.error).toHaveBeenCalledWith('Failed to load raid defense settings');
    });
    consoleErrorSpy.mockRestore();
  });
});
