import React from 'react';
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import AdminRoute from './AdminRoute';

vi.mock('../hooks/useAuth', () => ({ useAuth: vi.fn() }));
vi.mock('../hooks/useAdmin', () => ({ useAdmin: vi.fn() }));
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, Navigate: ({ to }) => <div>Navigate to {to}</div> };
});

import { useAuth } from '../hooks/useAuth';
import { useAdmin } from '../hooks/useAdmin';

const mockUseAuth = useAuth;
const mockUseAdmin = useAdmin;

describe('AdminRoute', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading when auth or admin is loading', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, loading: true });
    mockUseAdmin.mockReturnValue({ isAdmin: false, loading: true });
    render(
      <AdminRoute>
        <div>Secret</div>
      </AdminRoute>
    );
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('redirects to login when not authenticated', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, loading: false });
    mockUseAdmin.mockReturnValue({ isAdmin: false, loading: false });
    render(
      <AdminRoute>
        <div>Secret</div>
      </AdminRoute>
    );
    expect(screen.getByText('Navigate to /login')).toBeInTheDocument();
  });

  it('redirects to home when not admin', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, loading: false });
    mockUseAdmin.mockReturnValue({ isAdmin: false, loading: false });
    render(
      <AdminRoute>
        <div>Secret</div>
      </AdminRoute>
    );
    expect(screen.getByText('Navigate to /')).toBeInTheDocument();
  });

  it('renders children when authenticated and admin', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, loading: false });
    mockUseAdmin.mockReturnValue({ isAdmin: true, loading: false });
    render(
      <AdminRoute>
        <div>Secret</div>
      </AdminRoute>
    );
    expect(screen.getByText('Secret')).toBeInTheDocument();
  });
});
