import React from 'react';
import { render, screen, fireEvent, waitFor, waitForElementToBeRemoved } from '@testing-library/react';
import '@testing-library/jest-dom';
import axios from 'axios';
import GeneralSettings from './GeneralSettings';
import { toast } from 'sonner';

vi.mock('axios');
vi.mock('sonner');

const mockConfig = {
  prefix: '!',
  language: 'en',
  bot_enabled: true,
  test_mode: false,
};

describe('GeneralSettings', () => {
  beforeEach(() => {
    axios.get.mockResolvedValue({ data: mockConfig });
    axios.put.mockResolvedValue({ data: {} });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', async () => {
    render(<GeneralSettings guildId="123" />);
    expect(screen.getByText(/Loading.../i)).toBeInTheDocument();
    await waitForElementToBeRemoved(() => screen.getByText(/Loading.../i));
  });

  test('renders settings form after loading', async () => { // 1. Make the test function async
    render(<GeneralSettings guildId="123" />);

    // 2. Use an async "findBy" query to wait for an element
    //    that appears after your data fetch is complete.
    const settingLabel = await screen.findByText(/Command Prefix/i);
    expect(settingLabel).toBeInTheDocument();

    // 3. Now that you've waited, the rest of your assertions are safe
    //    and will not cause "act" warnings.
    expect(screen.getByLabelText(/Command Prefix/i)).toHaveValue(mockConfig.prefix);
    const languageButton = screen.getByRole('button', { name: /Language/i });
    expect(languageButton).toBeInTheDocument();
    expect(languageButton).toHaveTextContent(/en/i);
    expect(screen.getByLabelText(/Bot Enabled/i)).toBeChecked();
  });

  it('handles input changes', async () => {
    render(<GeneralSettings guildId="123" />);
    await waitFor(() => screen.getByLabelText(/Command Prefix/i));

    const prefixInput = screen.getByLabelText(/Command Prefix/i);
    fireEvent.change(prefixInput, { target: { value: '?' } });
    expect(prefixInput).toHaveValue('?');

    const botEnabledSwitch = screen.getByLabelText(/Bot Enabled/i);
    fireEvent.click(botEnabledSwitch);
    expect(botEnabledSwitch).not.toBeChecked();
  });

  it('saves settings and shows success toast', async () => {
    render(<GeneralSettings guildId="123" />);
    await waitFor(() => screen.getByText(/Save Changes/i));

    const saveButton = screen.getByText(/Save Changes/i);
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(axios.put).toHaveBeenCalledWith('/api/guilds/123/config/general', expect.any(Object));
      expect(toast.success).toHaveBeenCalledWith('General settings saved successfully');
    });
  });

  it('handles save error and shows error toast', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    axios.put.mockRejectedValue(new Error('Save failed'));
    render(<GeneralSettings guildId="123" />);
    await waitFor(() => screen.getByText(/Save Changes/i));

    const saveButton = screen.getByText(/Save Changes/i);
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to save general settings');
    });
    consoleErrorSpy.mockRestore();
  });

  it('resets settings on reset button click', async () => {
    render(<GeneralSettings guildId="123" />);

    // 1. Wait for the form to load initially
    const prefixInput = await screen.findByLabelText(/Command Prefix/i);
    const resetButton = screen.getByRole('button', { name: /reset/i });

    // 2. Change a value
    fireEvent.change(prefixInput, { target: { value: '?' } });
    expect(prefixInput).toHaveValue('?');

    // 3. Click the reset button
    fireEvent.click(resetButton);

    // 4. Wait for the form to reload/reset
    // The value should revert back to the mocked initial value
    await waitFor(() => {
      expect(screen.getByLabelText(/Command Prefix/i)).toHaveValue(mockConfig.prefix);
    });
  });

  it('shows an error message if fetching config fails', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    axios.get.mockRejectedValue(new Error('Fetch failed'));
    render(<GeneralSettings guildId="123" />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load settings/i)).toBeInTheDocument();
      expect(toast.error).toHaveBeenCalledWith('Failed to load general settings');
    });
    consoleErrorSpy.mockRestore();
  });
});