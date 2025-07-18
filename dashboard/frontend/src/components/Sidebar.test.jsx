import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';
import axios from 'axios';
import Sidebar from './Sidebar';

vi.mock('axios');
vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useParams: () => ({ guildId: '1' }),
    Link: ({ to, children }) => <a href={to}>{children}</a>,
  };
});

const guilds = [
  { id: '1', name: 'Guild One', icon: null },
  { id: '2', name: 'Guild Two', icon: 'icon2' },
];

describe('Sidebar', () => {
  beforeEach(() => {
    axios.get.mockResolvedValue({ data: guilds });
    axios.post.mockResolvedValue({});
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders guild list after fetch', async () => {
    render(
      <MemoryRouter>
        <Sidebar isOpen={true} />
      </MemoryRouter>
    );

    expect(await screen.findByText('Guild One')).toBeInTheDocument();
    expect(screen.getByText('Guild Two')).toBeInTheDocument();
  });

  it('displays error message on fetch failure', async () => {
    axios.get.mockRejectedValueOnce({ message: 'fail' });
    render(
      <MemoryRouter>
        <Sidebar isOpen={true} />
      </MemoryRouter>
    );
    expect(
      await screen.findByText(/Failed to fetch guilds/i)
    ).toBeInTheDocument();
  });

  it('refreshes guilds on button click', async () => {
    render(
      <MemoryRouter>
        <Sidebar isOpen={true} />
      </MemoryRouter>
    );
    await screen.findByText('Guild One');
    axios.get.mockResolvedValueOnce({ data: guilds });

    const button = screen.getByRole('button');
    fireEvent.click(button);
    await waitFor(() => expect(axios.post).toHaveBeenCalledWith('/api/guilds/refresh'));
  });
});
