import { expect, afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';

// Cleanup after each test case
afterEach(() => {
  cleanup();
});

// Mock requestAnimationFrame for animation tests
global.requestAnimationFrame = vi.fn((cb) => {
  setTimeout(cb, 0);
  return 0;
});

global.cancelAnimationFrame = vi.fn();

// Mock Plotly.js for component tests (heavy library)
vi.mock('react-plotly.js', () => ({
  default: ({ data, layout, config, ...props }: any) => (
    <div
      data-testid="plotly-plot"
      data-plot-data={JSON.stringify(data)}
      data-plot-layout={JSON.stringify(layout)}
      data-plot-config={JSON.stringify(config)}
      {...props}
    />
  )
}));

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Suppress console warnings in tests
global.console = {
  ...console,
  warn: vi.fn(),
  error: vi.fn(),
};
