import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import axios from 'axios';
import DashboardPage from './DashboardPage';

jest.mock('axios');

const mockStats = {
  total_guilds: 10,
  total_users: 100,
  commands_ran: 500,
};

const mockHealth = {
  uptime_seconds: 86461, // 1 day, 1 minute
};

describe('DashboardPage', () => {
  it('renders loading state initially', () => {
    axios.get.mockImplementation(() => new Promise(() => {}));
    render(<DashboardPage />);
    expect(screen.getByText(/Loading.../i)).toBeInTheDocument();
  });

  it('renders stats after successful data fetch', async () => {
    axios.get.mockImplementation((url) => {
      if (url === '/api/stats') {
        return Promise.resolve({ data: mockStats });
      }
      if (url === '/api/system/health') {
        return Promise.resolve({ data: mockHealth });
      }
      return Promise.reject(new Error('not found'));
    });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('Total Guilds')).toBeInTheDocument();
      expect(screen.getByText('10')).toBeInTheDocument();
      expect(screen.getByText('Total Users')).toBeInTheDocument();
      expect(screen.getByText('100')).toBeInTheDocument();
      expect(screen.getByText('Commands Ran')).toBeInTheDocument();
      expect(screen.getByText('500')).toBeInTheDocument();
      expect(screen.getByText('Uptime')).toBeInTheDocument();
      expect(screen.getByText(/1 day, 1 minute/i)).toBeInTheDocument();
    });
  });

  it('renders N/A when stats are not available', async () => {
    axios.get.mockImplementation((url) => {
      if (url === '/api/stats') {
        return Promise.resolve({ data: {} });
      }
      if (url === '/api/system/health') {
        return Promise.resolve({ data: { uptime_seconds: 0 } });
      }
      return Promise.reject(new Error('not found'));
    });

    render(<DashboardPage />);

    await waitFor(() => {
        expect(screen.getAllByText('N/A')).toHaveLength(4);
    });
  });

  it('renders error message on fetch failure', async () => {
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    axios.get.mockRejectedValue(new Error('API Error'));
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to fetch dashboard data./i)).toBeInTheDocument();
    });
    consoleErrorSpy.mockRestore();
  });
});