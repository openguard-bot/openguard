import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import axios from 'axios';
import ModerationSettings from './ModerationSettings';
import { toast } from 'sonner';

jest.mock('axios');
jest.mock('sonner');
jest.mock('./DiscordSelector', () => (props) => (
  <select
    data-testid={props.placeholder}
    value={props.value}
    onChange={(e) => props.onValueChange(e.target.value)}
  >
    <option value="1">Role 1</option>
    <option value="2">Role 2</option>
  </select>
));

const mockConfig = {
  action_confirmations: {
    warn: true,
    timeout: true,
    kick: false,
    ban: false,
  },
  suicidal_content_ping_role_id: '1',
  confirmation_ping_role_id: '2',
};

describe('ModerationSettings', () => {
  beforeEach(() => {
    axios.get.mockResolvedValue({ data: mockConfig });
    axios.put.mockResolvedValue({ data: {} });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', async () => {
    render(<ModerationSettings guildId="123" />);
    expect(screen.getByText(/Loading.../i)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText(/Loading.../i)).not.toBeInTheDocument());
  });

  it('renders settings form after loading', async () => {
    render(<ModerationSettings guildId="123" />);
    await waitFor(() => {
      expect(screen.getByLabelText(/Warn Confirmation/i)).toBeChecked();
      expect(screen.getByLabelText(/Kick Confirmation/i)).not.toBeChecked();
      const suicidalRoleSelect = screen.getByTestId('Select a role for suicidal content pings...');
      expect(suicidalRoleSelect).toHaveValue(mockConfig.suicidal_content_ping_role_id);
      const confirmationRoleSelect = screen.getByTestId('Select a role for confirmation pings...');
      expect(confirmationRoleSelect).toHaveValue(mockConfig.confirmation_ping_role_id);
    });
  });

  it('handles switch changes', async () => {
    render(<ModerationSettings guildId="123" />);
    await waitFor(() => screen.getByLabelText(/Warn Confirmation/i));

    const warnSwitch = screen.getByLabelText(/Warn Confirmation/i);
    fireEvent.click(warnSwitch);
    expect(warnSwitch).not.toBeChecked();
  });

  it('handles role selection change', async () => {
    render(<ModerationSettings guildId="123" />);
    await waitFor(() => screen.getByTestId('Select a role for suicidal content pings...'));

    const roleSelect = screen.getByTestId('Select a role for suicidal content pings...');
    fireEvent.change(roleSelect, { target: { value: '2' } });
    expect(roleSelect).toHaveValue('2');
  });

  it('saves settings and shows success toast', async () => {
    render(<ModerationSettings guildId="123" />);
    await waitFor(() => screen.getByText(/Save Changes/i));

    const saveButton = screen.getByText(/Save Changes/i);
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(axios.put).toHaveBeenCalledWith('/api/guilds/123/config/moderation', expect.any(Object));
      expect(toast.success).toHaveBeenCalledWith('Moderation settings saved successfully');
    });
  });

  it('shows an error message if fetching config fails', async () => {
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    axios.get.mockRejectedValue(new Error('Fetch failed'));
    render(<ModerationSettings guildId="123" />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load settings/i)).toBeInTheDocument();
      expect(toast.error).toHaveBeenCalledWith('Failed to load moderation settings');
    });
    consoleErrorSpy.mockRestore();
  });
});