import { render, screen } from '@testing-library/react';
import App from './App';
import { AuthProvider } from './contexts/AuthContext';
import axios from 'axios';
import { vi } from 'vitest';

// Mock window.location for BrowserRouter
const originalLocation = window.location;

beforeAll(() => {
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { ...originalLocation, pathname: '/dashboard' },
  });

  // Mock window.matchMedia
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation(query => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(), // Deprecated
      removeListener: vi.fn(), // Deprecated
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });

  // Mock axios to simulate a logged-in user
  axios.get = vi.fn((url) => {
    if (url === '/api/users/@me') {
      return Promise.resolve({ data: { id: '123', username: 'testuser' } });
    }
    return Promise.reject(new Error('not found'));
  });
});

afterAll(() => {
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: originalLocation,
  });
  vi.restoreAllMocks();
});

test('renders without crashing', () => {
  render(
    <AuthProvider>
      <App />
    </AuthProvider>
  );
});

test('renders OpenGuard Dashboard text', () => {
  render(
    <AuthProvider>
      <App />
    </AuthProvider>
  );
  const linkElement = screen.getByText(/OpenGuard Dashboard/i, { hidden: true });
  expect(linkElement).toBeInTheDocument();
  expect(linkElement).not.toBeVisible();
});
