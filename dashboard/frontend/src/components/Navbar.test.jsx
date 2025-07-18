import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';
import Navbar from './Navbar';

const setTheme = vi.fn();
const logout = vi.fn();
const navigate = vi.fn();

vi.mock('next-themes', () => ({ useTheme: () => ({ theme: 'light', setTheme }) }));
vi.mock('../hooks/useAuth', () => ({ useAuth: () => ({ user: { id: '1', username: 'U', avatar: 'a' }, logout }) }));
vi.mock('../hooks/useAdmin', () => ({ useAdmin: () => ({ isAdmin: true }) }));
vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return { ...actual, useNavigate: () => navigate };
});
vi.mock('./ui/dropdown-menu', () => ({
  DropdownMenu: ({ children }) => <div>{children}</div>,
  DropdownMenuTrigger: ({ children }) => <div>{children}</div>,
  DropdownMenuContent: ({ children }) => <div>{children}</div>,
  DropdownMenuItem: ({ children, onClick }) => (
    <div onClick={onClick}>{children}</div>
  ),
  DropdownMenuLabel: ({ children }) => <div>{children}</div>,
  DropdownMenuSeparator: () => <hr />,
}));

describe('Navbar', () => {
  it('navigates to admin panel when button clicked', () => {
    render(
      <MemoryRouter>
        <Navbar toggleSidebar={() => {}} />
      </MemoryRouter>
    );
    const adminButton = screen.getByText(/Admin Panel/i);
    fireEvent.click(adminButton);
    expect(navigate).toHaveBeenCalledWith('/admin/dashboard');
  });

  it('toggles dark mode', () => {
    render(
      <MemoryRouter>
        <Navbar toggleSidebar={() => {}} />
      </MemoryRouter>
    );
    const switchEl = screen.getByRole('switch');
    fireEvent.click(switchEl);
    expect(setTheme).toHaveBeenCalledWith('dark');
  });

  it('logs out via menu item', async () => {
    render(
      <MemoryRouter>
        <Navbar toggleSidebar={() => {}} />
      </MemoryRouter>
    );
    const avatarButton = screen.getAllByRole('button')[2];
    fireEvent.pointerDown(avatarButton);
    fireEvent.click(avatarButton);
    const logoutItem = await screen.findByText('Log out');
    fireEvent.click(logoutItem);
    expect(logout).toHaveBeenCalled();
  });
});
