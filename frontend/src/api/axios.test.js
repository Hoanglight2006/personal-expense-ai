import { beforeEach, describe, expect, it, vi } from 'vitest';
import api from './axios';

const rejectWithStatus = (url, status) => () => Promise.reject({
  config: { url },
  response: { status },
});

beforeEach(() => {
  localStorage.clear();
});

describe('API authentication interceptor', () => {
  it('clears an expired token and announces unauthorized protected requests', async () => {
    localStorage.setItem('access_token', 'expired-test-token');
    const unauthorized = vi.fn();
    window.addEventListener('auth:unauthorized', unauthorized, { once: true });

    await expect(api.get('/categories', {
      adapter: rejectWithStatus('/categories', 401),
    })).rejects.toBeTruthy();

    expect(localStorage.getItem('access_token')).toBeNull();
    expect(unauthorized).toHaveBeenCalledTimes(1);
  });

  it('does not turn an expected login 401 into a global logout event', async () => {
    localStorage.setItem('access_token', 'existing-test-token');
    const unauthorized = vi.fn();
    window.addEventListener('auth:unauthorized', unauthorized, { once: true });

    await expect(api.post('/auth/login', null, {
      adapter: rejectWithStatus('/auth/login', 401),
    })).rejects.toBeTruthy();

    expect(localStorage.getItem('access_token')).toBe('existing-test-token');
    expect(unauthorized).not.toHaveBeenCalled();
  });
});
