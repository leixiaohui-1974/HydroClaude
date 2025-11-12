/**
 * Performance Benchmarks
 *
 * Measures rendering performance of key components
 * Run with: npm run benchmark (if configured)
 *
 * Note: This file demonstrates performance testing approach.
 * For actual benchmarking, integrate with tools like:
 * - @vitest/bench
 * - Playwright Performance APIs
 * - Chrome DevTools Performance
 */

import { describe, bench } from 'vitest';
import { render } from '@testing-library/react';
import Plot3D from '../features/simulation/components/Plot3D';
import EnhancedCharts from '../features/simulation/components/EnhancedCharts';
import AnimationController from '../features/simulation/components/AnimationController';

// Mock data generators
const generateMockData = (gridPoints: number, timeSteps: number) => {
  const x = Array.from({ length: gridPoints }, (_, i) => i * 10);
  const time = Array.from({ length: timeSteps }, (_, i) => i * 0.5);

  const h: number[][] = [];
  const V: number[][] = [];
  const Q: number[][] = [];

  for (let t = 0; t < timeSteps; t++) {
    const hRow: number[] = [];
    const vRow: number[] = [];
    const qRow: number[] = [];

    for (let i = 0; i < gridPoints; i++) {
      hRow.push(1.0 + 0.5 * Math.sin(i * 0.1 + t * 0.2));
      vRow.push(0.5 + 0.3 * Math.cos(i * 0.1 + t * 0.2));
      qRow.push(hRow[i] * vRow[i]);
    }

    h.push(hRow);
    V.push(vRow);
    Q.push(qRow);
  }

  return { x, time, h, V, Q };
};

describe('Component Rendering Performance', () => {
  describe('Small Dataset (50 points, 20 steps)', () => {
    const { x, time, h, V, Q } = generateMockData(50, 20);

    bench('Plot3D initial render', () => {
      render(<Plot3D x={x} time={time} h={h} V={V} Q={Q} variable="h" />);
    });

    bench('EnhancedCharts initial render', () => {
      render(<EnhancedCharts x={x} time={time} h={h} V={V} Q={Q} />);
    });

    bench('AnimationController initial render', () => {
      render(
        <AnimationController
          totalFrames={time.length}
          currentFrame={0}
          onFrameChange={() => {}}
        />
      );
    });
  });

  describe('Medium Dataset (200 points, 100 steps)', () => {
    const { x, time, h, V, Q } = generateMockData(200, 100);

    bench('Plot3D initial render', () => {
      render(<Plot3D x={x} time={time} h={h} V={V} Q={Q} variable="h" />);
    });

    bench('EnhancedCharts initial render', () => {
      render(<EnhancedCharts x={x} time={time} h={h} V={V} Q={Q} />);
    });
  });

  describe('Large Dataset (500 points, 200 steps)', () => {
    const { x, time, h, V, Q } = generateMockData(500, 200);

    bench('Plot3D initial render', () => {
      render(<Plot3D x={x} time={time} h={h} V={V} Q={Q} variable="h" />);
    }, { iterations: 10 }); // Reduce iterations for large datasets

    bench('EnhancedCharts initial render', () => {
      render(<EnhancedCharts x={x} time={time} h={h} V={V} Q={Q} />);
    }, { iterations: 10 });
  });

  describe('Re-render Performance (memoization test)', () => {
    const { x, time, h, V, Q } = generateMockData(100, 50);

    bench('Plot3D re-render with same props', () => {
      const { rerender } = render(
        <Plot3D x={x} time={time} h={h} V={V} Q={Q} variable="h" />
      );
      // Re-render with same props - should be fast due to memo()
      rerender(<Plot3D x={x} time={time} h={h} V={V} Q={Q} variable="h" />);
    });

    bench('Plot3D re-render with different variable', () => {
      const { rerender } = render(
        <Plot3D x={x} time={time} h={h} V={V} Q={Q} variable="h" />
      );
      // Re-render with different variable - will re-render
      rerender(<Plot3D x={x} time={time} h={h} V={V} Q={Q} variable="V" />);
    });
  });
});

/**
 * Manual Performance Testing Guide
 *
 * To test performance in the browser:
 *
 * 1. Open Chrome DevTools
 * 2. Go to Performance tab
 * 3. Click Record
 * 4. Interact with the app (switch tabs, animate, etc.)
 * 5. Stop recording
 * 6. Analyze:
 *    - FPS (should be >30 during animation)
 *    - Scripting time
 *    - Rendering time
 *    - Memory usage
 *
 * Expected Performance Targets:
 * - Small dataset (50 points): 30+ FPS, <500ms initial render
 * - Medium dataset (200 points): 20-30 FPS, <2s initial render
 * - Large dataset (500 points): 10-20 FPS, <5s initial render
 *
 * Optimization Checklist:
 * ✓ React.memo() on expensive components
 * ✓ useMemo() for expensive calculations
 * ✓ useCallback() for callbacks passed to memoized children
 * ✓ Code splitting for large libraries (Plotly)
 * ✓ Lazy loading for route-level components
 * □ Virtual scrolling for large lists (future)
 * □ Web Workers for heavy computation (future)
 */
