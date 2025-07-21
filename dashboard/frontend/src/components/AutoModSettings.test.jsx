import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import axios from 'axios';
import { vi } from 'vitest';
import AutoModSettings from './AutoModSettings';
import { toast } from 'sonner';

vi.mock('axios');
vi.mock('sonner');

const mockRules = [{ id: '1', name: 'Test Rule' }];

describe('AutoModSettings', () => {
  beforeEach(() => {
    axios.get.mockResolvedValue({ data: mockRules });
    axios.post.mockResolvedValue({ data: { regex: 'test' } });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', async () => {
    render(<AutoModSettings guildId="123" />);
    expect(screen.getByText(/Loading.../i)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText(/Loading.../i)).not.toBeInTheDocument());
  });

  it('displays rules after loading', async () => {
    render(<AutoModSettings guildId="123" />);
    await waitFor(() => expect(screen.getByText(/Test Rule/i)).toBeInTheDocument());
  });
});
