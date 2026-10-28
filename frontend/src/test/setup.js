import '@testing-library/jest-dom/vitest';
import { cleanup, configure } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

// Increase timeout for async queries on CI runners
configure({ asyncUtilTimeout: 15000 });

// Mock window methods that are not implemented in jsdom
if (typeof window !== 'undefined') {
  window.scrollTo = vi.fn();
}

afterEach(() => {
  cleanup();
});
