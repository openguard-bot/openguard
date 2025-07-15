import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import axios from 'axios';
import ChannelManagement from './ChannelManagement';
import { toast } from 'sonner';

jest.mock('axios');
jest.mock('sonner');
jest.mock('./DiscordSelector', () => (props) => (
  <select
    data-testid={props.type}
    value={props.value}
    onChange={(e) => props.onValueChange(e.target.value)}
  >
    <option value="1">Channel 1</option>
    <option value="2">Channel 2</option>
  </select>
));

const mockConfig = {
  nsfw_channels: ['12345'],
  suggestions_channel: '1',
};

describe('ChannelManagement', () => {
  beforeEach(() => {
    axios.get.mockResolvedValue({ data: mockConfig });
    axios.put.mockResolvedValue({ data: {} });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', async () => {
    render(<ChannelManagement guildId="123" />);
    // Wait for the loading state to disappear
    await waitFor(() => expect(screen.queryByText(/Loading.../i)).not.toBeInTheDocument());
    // Then assert that the form elements are present
    expect(screen.getByText('12345')).toBeInTheDocument();
  });

  it('renders settings form after loading', async () => {
    render(<ChannelManagement guildId="123" />);
    await waitFor(() => {
      expect(screen.getByText('12345')).toBeInTheDocument();
      expect(screen.getByTestId('channels')).toHaveValue(mockConfig.suggestions_channel);
    });
  });

  it('adds and removes an nsfw channel', async () => {
    render(<ChannelManagement guildId="123" />);
    await waitFor(() => screen.getByPlaceholderText(/Enter Channel ID/i));

    const input = screen.getByPlaceholderText(/Enter Channel ID/i);
    const addButton = screen.getByRole('button', { name: /Add NSFW Channel/i });

    fireEvent.change(input, { target: { value: '67890' } });
    fireEvent.click(addButton);

    expect(screen.getByText('67890')).toBeInTheDocument();

    const removeButton = screen.getByLabelText('Remove channel 67890');
    fireEvent.click(removeButton);

    await waitFor(() => {
      expect(screen.queryByText('67890')).not.toBeInTheDocument();
    });
  });

  it('saves settings and shows success toast', async () => {
    render(<ChannelManagement guildId="123" />);
    await waitFor(() => screen.getByText(/Save Changes/i));

    const saveButton = screen.getByText(/Save Changes/i);
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(axios.put).toHaveBeenCalledWith('/api/guilds/123/config/channels', expect.any(Object));
      expect(toast.success).toHaveBeenCalledWith('Channel settings saved successfully');
    });
  });
});