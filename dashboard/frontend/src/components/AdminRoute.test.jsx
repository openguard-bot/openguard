import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import AdminRoute from './AdminRoute';

let authState;
let adminState;
vi.mock('../hooks/useAuth.js', () => ({
  useAuth: () => authState,
}));
vi.mock('../hooks/useAdmin.js', () => ({
  useAdmin: () => adminState,
}));

const mockHooks = (auth, admin) => {
  authState = auth;
  adminState = admin;
};

describe('AdminRoute', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('redirects to login when not authenticated', () => {
    mockHooks({ isAuthenticated: false, loading: false }, { isAdmin: false, loading: false });
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route path="/admin" element={<AdminRoute><div>Admin</div></AdminRoute>} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText('Login Page')).toBeInTheDocument();
  });

  it('redirects to home when not an admin', () => {
    mockHooks({ isAuthenticated: true, loading: false }, { isAdmin: false, loading: false });
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route path="/" element={<div>Home</div>} />
          <Route path="/admin" element={<AdminRoute><div>Admin</div></AdminRoute>} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText('Home')).toBeInTheDocument();
  });

  it('renders children when authenticated and admin', () => {
    mockHooks({ isAuthenticated: true, loading: false }, { isAdmin: true, loading: false });
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route path="/admin" element={<AdminRoute><div>Admin</div></AdminRoute>} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText('Admin')).toBeInTheDocument();
  });
});
