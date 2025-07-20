import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import axios from 'axios';
import AISettings from './AISettings';
import { toast } from 'sonner';

vi.mock('axios');
vi.mock('sonner');

const mockConfig = {
  analysis_mode: 'all',
  keyword_rules: [],
  bot_enabled: true,
  test_mode: false,
};

describe('AISettings', () => {
  beforeEach(() => {
    axios.get.mockResolvedValue({ data: mockConfig });
    axios.put.mockResolvedValue({ data: {} });
    axios.post.mockResolvedValue({ data: {} });
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
    });
  });

  it('handles input changes', async () => {
    render(<AISettings guildId="123" />);
    await waitFor(() => screen.getByLabelText(/AI Test Mode/i));

    const testModeSwitch = screen.getByLabelText(/AI Test Mode/i);
    fireEvent.click(testModeSwitch);
    expect(testModeSwitch).toBeChecked();
  });

  it('allows adding a keyword rule', async () => {
    render(<AISettings guildId="123" />);
    
    // Wait for the component to finish loading
    await waitFor(() => expect(screen.queryByText(/Loading.../i)).not.toBeInTheDocument());

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
});