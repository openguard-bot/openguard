import { renderHook, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import axios from 'axios';
import { useAdmin } from './useAdmin';

vi.mock('axios');
vi.mock('./useAuth', () => ({ useAuth: vi.fn() }));

import { useAuth } from './useAuth';

const mockUseAuth = useAuth;

describe('useAdmin', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('returns true when user id is in owners list', async () => {
    mockUseAuth.mockReturnValue({ user: { id: '1' } });
    axios.get.mockResolvedValue({ data: [1, 2] });
    const { result } = renderHook(() => useAdmin());
    await waitFor(() => axios.get.mock.calls.length > 0);
    await waitFor(() => result.current.isAdmin === true);
    expect(result.current.isAdmin).toBe(true);
  });

  it('returns false when user id not in owners list', async () => {
    mockUseAuth.mockReturnValue({ user: { id: '1' } });
    axios.get.mockResolvedValue({ data: [3, 4] });
    const { result } = renderHook(() => useAdmin());
    await waitFor(() => axios.get.mock.calls.length > 0);
    await waitFor(() => result.current.loading === false);
    expect(result.current.isAdmin).toBe(false);
  });

  it('handles missing user gracefully', async () => {
    mockUseAuth.mockReturnValue({ user: null });
    axios.get.mockResolvedValue({ data: [] });
    const { result } = renderHook(() => useAdmin());
    await waitFor(() => result.current.loading === false);
    expect(result.current.isAdmin).toBe(false);
  });
});
