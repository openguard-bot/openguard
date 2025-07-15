import React from 'react';
import { render, screen, fireEvent, waitFor, act, waitForElementToBeRemoved } from '@testing-library/react';
import '@testing-library/jest-dom';
import axios from 'axios';
import LoggingSettings from './LoggingSettings';
import { toast } from 'sonner';

vi.mock('axios');
vi.mock('sonner');

const mockConfig = {
  webhook_url: 'https://discord.com/api/webhooks/123/abc',
  enabled_events: {
    member_join: true,
    member_remove: false,
  },
};

describe('LoggingSettings', () => {
  beforeEach(() => {
    axios.get.mockResolvedValue({ data: mockConfig });
    axios.put.mockResolvedValue({ data: {} });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', async () => {
    render(<LoggingSettings guildId="123" />);
    expect(screen.getByText(/Loading.../i)).toBeInTheDocument();
    await waitForElementToBeRemoved(() => screen.getByText(/Loading.../i));
  });

  test('renders settings form after loading', async () => { // 1. Make the test function async
    render(<LoggingSettings guildId="123" />);

    // 2. Use an async "findBy" query to wait for an element
    //    that appears after your data fetch is complete.
    expect(await screen.findByText('Event Logging', { selector: '[data-slot="card-title"]' })).toBeInTheDocument();

    // 3. Now that you've waited, the rest of your assertions are safe
    //    and will not cause "act" warnings.
    expect(screen.getByLabelText(/Logging Webhook URL/i)).toBeInTheDocument();
    expect(screen.getByLabelText('Member Join', { selector: '#member_join' })).toBeChecked();
    expect(screen.getByLabelText('Member Remove', { selector: '#member_remove' })).not.toBeChecked();
  });

  it('handles input changes', async () => {
    render(<LoggingSettings guildId="123" />);
    const webhookInput = await screen.findByLabelText(/Logging Webhook URL/i);
    fireEvent.change(webhookInput, { target: { value: 'https://new-webhook.com' } });
    expect(webhookInput).toHaveValue('https://new-webhook.com');

    const memberRemoveSwitch = screen.getByLabelText('Member Remove', { selector: '#member_remove' });
    fireEvent.click(memberRemoveSwitch);
    expect(memberRemoveSwitch).toBeChecked();
  });

  it('saves settings and shows success toast', async () => {
    render(<LoggingSettings guildId="123" />);
    await screen.findByText(/Save Changes/i);

    const saveButton = screen.getByText(/Save Changes/i);
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(axios.put).toHaveBeenCalledWith('/api/guilds/123/config/logging', expect.any(Object));
      expect(toast.success).toHaveBeenCalledWith('Logging settings saved successfully');
    });
  });
});