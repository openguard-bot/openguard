import React from 'react';
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import ProtectedRoute from './ProtectedRoute';

vi.mock('../hooks/useAuth', () => ({ useAuth: vi.fn() }));
vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return { ...actual, Navigate: ({ to }) => <div>Navigate to {to}</div> };
});

import { useAuth } from '../hooks/useAuth';

const mockUseAuth = useAuth;

describe('ProtectedRoute', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading when auth is loading', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, loading: true });
    render(
      <ProtectedRoute>
        <div>Secret</div>
      </ProtectedRoute>
    );
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('redirects to login when not authenticated', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, loading: false });
    render(
      <ProtectedRoute>
        <div>Secret</div>
      </ProtectedRoute>
    );
    expect(screen.getByText('Navigate to /login')).toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, loading: false });
    render(
      <ProtectedRoute>
        <div>Secret</div>
      </ProtectedRoute>
    );
    expect(screen.getByText('Secret')).toBeInTheDocument();
  });
});