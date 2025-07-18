import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import ProtectedRoute from './ProtectedRoute';

let authState;
vi.mock('../hooks/useAuth.js', () => ({
  useAuth: () => authState,
}));

const mockUseAuth = (state) => {
  authState = state;
};

describe('ProtectedRoute', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading indicator when auth is loading', () => {
    mockUseAuth({ isAuthenticated: false, loading: true });
    render(
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route path="/protected" element={<ProtectedRoute><div>Protected</div></ProtectedRoute>} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText(/Loading.../i)).toBeInTheDocument();
  });

  it('redirects to login when not authenticated', () => {
    mockUseAuth({ isAuthenticated: false, loading: false });
    render(
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route path="/protected" element={<ProtectedRoute><div>Protected</div></ProtectedRoute>} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText('Login Page')).toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    mockUseAuth({ isAuthenticated: true, loading: false });
    render(
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route path="/protected" element={<ProtectedRoute><div>Protected</div></ProtectedRoute>} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText('Protected')).toBeInTheDocument();
  });
});
