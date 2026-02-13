import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import React from 'react';

declare var global: typeof globalThis;

// Cleanup after each test case
afterEach(() => {
  cleanup();
});

// Mock requestAnimationFrame for animation tests
// Simple mock that can work with both real and fake timers
let rafId = 0;
const rafCallbacks = new Map<number, FrameRequestCallback>();

global.requestAnimationFrame = vi.fn((cb: FrameRequestCallback) => {
  const id = ++rafId;
  rafCallbacks.set(id, cb);
  // Use setImmediate-like behavior via setTimeout with 0 delay
  setTimeout(() => {
    const callback = rafCallbacks.get(id);
    if (callback) {
      rafCallbacks.delete(id);
      callback(performance.now());
    }
  }, 0);
  return id;
});

global.cancelAnimationFrame = vi.fn((id: number) => {
  rafCallbacks.delete(id);
});

// Mock Plotly.js for component tests (heavy library)
vi.mock('react-plotly.js', () => ({
  default: ({ data, layout, config, ...props }: any) =>
    React.createElement('div', {
      'data-testid': 'plotly-plot',
      'data-plot-data': JSON.stringify(data),
      'data-plot-layout': JSON.stringify(layout),
      'data-plot-config': JSON.stringify(config),
      ...props
    })
}));

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Mock window.matchMedia (required by Ant Design)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
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

// Suppress console warnings in tests
global.console = {
  ...console,
  warn: vi.fn(),
  error: vi.fn(),
};
