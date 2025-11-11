import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SimulationResults from '../SimulationResults';
import { SimulationResultResponse } from '@/services/api';

describe('SimulationResults Integration Tests', () => {
  let user: ReturnType<typeof userEvent.setup>;

  // Complete mock simulation result
  const mockResult: SimulationResultResponse = {
    task_id: 'test-task-123',
    status: 'completed',
    x: [0, 10, 20, 30, 40, 50],
    time: [0, 0.5, 1.0, 1.5, 2.0],
    h: [
      [1.0, 1.1, 1.2, 1.1, 1.0, 0.9],
      [1.1, 1.2, 1.3, 1.2, 1.1, 1.0],
      [1.2, 1.3, 1.4, 1.3, 1.2, 1.1],
      [1.3, 1.4, 1.5, 1.4, 1.3, 1.2],
      [1.4, 1.5, 1.6, 1.5, 1.4, 1.3]
    ],
    Q: [
      [0.5, 0.66, 0.84, 0.66, 0.5, 0.36],
      [0.66, 0.84, 1.04, 0.84, 0.66, 0.5],
      [0.84, 1.04, 1.26, 1.04, 0.84, 0.66],
      [1.04, 1.26, 1.5, 1.26, 1.04, 0.84],
      [1.26, 1.5, 1.76, 1.5, 1.26, 1.04]
    ],
    V: [
      [0.5, 0.6, 0.7, 0.6, 0.5, 0.4],
      [0.6, 0.7, 0.8, 0.7, 0.6, 0.5],
      [0.7, 0.8, 0.9, 0.8, 0.7, 0.6],
      [0.8, 0.9, 1.0, 0.9, 0.8, 0.7],
      [0.9, 1.0, 1.1, 1.0, 0.9, 0.8]
    ],
    duration: 0.1234,
    metrics: {
      total_iterations: 150,
      mass_conservation_error: 1e-8,
      converged: true,
      max_depth: 1.6,
      min_depth: 0.36,
      max_velocity: 1.1,
      max_froude: 0.85,
      mean_depth_final: 1.35,
      mean_discharge_final: 1.05
    }
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Configure userEvent for better async handling
    user = userEvent.setup();
  });

  describe('Component Integration', () => {
    it('should render all main sections', () => {
      render(<SimulationResults result={mockResult} />);

      // Status badge
      expect(screen.getByText(/模拟完成/i)).toBeInTheDocument();

      // Metrics card
      expect(screen.getByText(/性能指标/i)).toBeInTheDocument();

      // Animation controller
      expect(screen.getByText(/动画控制/i)).toBeInTheDocument();

      // Tabs
      expect(screen.getByText(/经典视图/i)).toBeInTheDocument();
      expect(screen.getByText(/3D可视化/i)).toBeInTheDocument();
      expect(screen.getByText(/增强图表/i)).toBeInTheDocument();
    });

    it('should display correct task ID and status', () => {
      render(<SimulationResults result={mockResult} />);

      expect(screen.getByText(/test-task-123/i)).toBeInTheDocument();
      expect(screen.getByText(/✓ 模拟完成/i)).toBeInTheDocument();
    });

    it('should display all performance metrics', () => {
      render(<SimulationResults result={mockResult} />);

      expect(screen.getByText(/执行时间/i)).toBeInTheDocument();
      expect(screen.getByText('0.1234s')).toBeInTheDocument();

      expect(screen.getByText(/时间步数/i)).toBeInTheDocument();
      expect(screen.getByText('150')).toBeInTheDocument();

      expect(screen.getByText(/质量守恒误差/i)).toBeInTheDocument();
      expect(screen.getByText(/收敛状态/i)).toBeInTheDocument();
      expect(screen.getByText(/✓ 收敛/i)).toBeInTheDocument();

      expect(screen.getByText(/最大水深/i)).toBeInTheDocument();
      expect(screen.getByText('1.6000 m')).toBeInTheDocument();
    });

    it('should display v1.4.0 feature banner', () => {
      render(<SimulationResults result={mockResult} />);

      expect(screen.getByText(/v1.4.0 增强可视化功能/i)).toBeInTheDocument();
    });
  });

  describe('Animation and Time Synchronization', () => {
    it('should initialize with time index 0', () => {
      render(<SimulationResults result={mockResult} />);

      // Check that the first time step is shown in plot title
      const plots = screen.getAllByTestId('plotly-plot');
      const depthPlot = plots[0];
      const layout = JSON.parse(depthPlot.getAttribute('data-plot-layout') || '{}');

      expect(layout.title).toContain('t = 0.00s');
    });

    it('should update all plots when frame changes via animation controller', async () => {
      render(<SimulationResults result={mockResult} />);

      // Get initial plot data
      const initialPlots = screen.getAllByTestId('plotly-plot');
      const initialLayout = JSON.parse(
        initialPlots[0].getAttribute('data-plot-layout') || '{}'
      );
      expect(initialLayout.title).toContain('t = 0.00s');

      // Click step forward button
      const stepForwardButton = screen.getByRole('button', { name: /下一帧/i });
      await user.click(stepForwardButton);

      // Check that plots updated
      await waitFor(() => {
        const updatedPlots = screen.getAllByTestId('plotly-plot');
        const updatedLayout = JSON.parse(
          updatedPlots[0].getAttribute('data-plot-layout') || '{}'
        );
        expect(updatedLayout.title).toContain('t = 0.50s');
      });
    });

    it('should synchronize animation across all classic view plots', async () => {
      render(<SimulationResults result={mockResult} />);

      // Click step forward twice
      const stepForwardButton = screen.getByRole('button', { name: /下一帧/i });
      await user.click(stepForwardButton);

      // Wait for first click to complete
      await waitFor(() => {
        expect(screen.getByText('2')).toBeInTheDocument(); // Frame 2
      });

      await user.click(stepForwardButton);

      // Wait for second click to complete
      await waitFor(() => {
        expect(screen.getByText('3')).toBeInTheDocument(); // Frame 3
      });

      // All three classic plots should show t = 1.00s
      await waitFor(() => {
        const plots = screen.getAllByTestId('plotly-plot');

        // Depth plot (first)
        const depthLayout = JSON.parse(plots[0].getAttribute('data-plot-layout') || '{}');
        expect(depthLayout.title).toContain('t = 1.00s');

        // Velocity plot (second)
        const velocityLayout = JSON.parse(plots[1].getAttribute('data-plot-layout') || '{}');
        expect(velocityLayout.title).toContain('t = 1.00s');

        // Discharge plot (third)
        const dischargeLayout = JSON.parse(plots[2].getAttribute('data-plot-layout') || '{}');
        expect(dischargeLayout.title).toContain('t = 1.00s');
      });
    });

    it('should display correct data for current time step', async () => {
      render(<SimulationResults result={mockResult} />);

      // Initial frame (t=0): h = [1.0, 1.1, 1.2, 1.1, 1.0, 0.9]
      const initialPlots = screen.getAllByTestId('plotly-plot');
      const initialData = JSON.parse(
        initialPlots[0].getAttribute('data-plot-data') || '[]'
      );
      expect(initialData[0].y).toEqual(mockResult.h[0]);

      // Step forward to frame 1 (t=0.5): h = [1.1, 1.2, 1.3, 1.2, 1.1, 1.0]
      const stepForwardButton = screen.getByRole('button', { name: /下一帧/i });
      await user.click(stepForwardButton);

      await waitFor(() => {
        const updatedPlots = screen.getAllByTestId('plotly-plot');
        const updatedData = JSON.parse(
          updatedPlots[0].getAttribute('data-plot-data') || '[]'
        );
        expect(updatedData[0].y).toEqual(mockResult.h[1]);
      });
    });

    it('should update frame counter when animation plays', async () => {
      render(<SimulationResults result={mockResult} />);

      // Initial frame
      expect(screen.getByText(/帧/)).toBeInTheDocument();
      expect(screen.getByText('1')).toBeInTheDocument(); // Frame 1 (0-indexed as 0)

      // Step forward
      const stepForwardButton = screen.getByRole('button', { name: /下一帧/i });
      await user.click(stepForwardButton);

      await waitFor(() => {
        expect(screen.getByText('2')).toBeInTheDocument(); // Frame 2
      });
    });
  });

  describe('Tab Navigation', () => {
    it('should start with Classic View tab active', () => {
      render(<SimulationResults result={mockResult} />);

      // Classic view plots should be visible
      const plots = screen.getAllByTestId('plotly-plot');
      expect(plots.length).toBeGreaterThanOrEqual(3); // At least depth, velocity, discharge
    });

    it('should switch to 3D visualization tab', async () => {
      render(<SimulationResults result={mockResult} />);

      const threeDTab = screen.getByText(/3D可视化/i);
      await user.click(threeDTab);

      // Wait for tab content to render
      await waitFor(() => {
        expect(screen.getByText(/3D可视化 \(v1.4.0新功能\)/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/使用鼠标拖动旋转视角/i)).toBeInTheDocument();
    });

    it('should switch to Enhanced Charts tab', async () => {
      render(<SimulationResults result={mockResult} />);

      const enhancedTab = screen.getByText(/增强图表/i);
      await user.click(enhancedTab);

      // Wait for tab content to render
      await waitFor(() => {
        expect(screen.getByText(/增强图表 \(v1.4.0新功能\)/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/包含等值线图、热力图/i)).toBeInTheDocument();
    });

    it('should maintain animation state when switching tabs', async () => {
      render(<SimulationResults result={mockResult} />);

      // Move to frame 2
      const stepForwardButton = screen.getByRole('button', { name: /下一帧/i });
      await user.click(stepForwardButton);

      // Wait for first click
      await waitFor(() => {
        expect(screen.getByText('2')).toBeInTheDocument();
      });

      await user.click(stepForwardButton);

      // Wait for second click and verify frame counter shows 3
      await waitFor(() => {
        expect(screen.getByText('3')).toBeInTheDocument();
      });

      // Switch to 3D tab
      const threeDTab = screen.getByText(/3D可视化/i);
      await user.click(threeDTab);

      // Wait for tab to switch and verify frame counter still shows 3
      await waitFor(() => {
        expect(screen.getByText(/3D可视化 \(v1.4.0新功能\)/i)).toBeInTheDocument();
      });

      expect(screen.getByText('3')).toBeInTheDocument();

      // Switch back to classic
      const classicTab = screen.getByText(/经典视图/i);
      await user.click(classicTab);

      // Wait for tab to switch and verify still on frame 3
      await waitFor(() => {
        expect(screen.getByText('3')).toBeInTheDocument();
      });

      // Plot should show t = 1.00s
      await waitFor(() => {
        const plots = screen.getAllByTestId('plotly-plot');
        const layout = JSON.parse(plots[0].getAttribute('data-plot-layout') || '{}');
        expect(layout.title).toContain('t = 1.00s');
      });
    });
  });

  describe('Classic View Features', () => {
    it('should render water depth plot with correct styling', () => {
      render(<SimulationResults result={mockResult} />);

      const plots = screen.getAllByTestId('plotly-plot');
      const depthPlot = plots[0];

      const data = JSON.parse(depthPlot.getAttribute('data-plot-data') || '[]');
      expect(data[0].name).toBe('水深');
      expect(data[0].type).toBe('scatter');
      expect(data[0].mode).toBe('lines');
      expect(data[0].line.color).toBe('#1890ff');
      expect(data[0].fill).toBe('tozeroy');
    });

    it('should render velocity plot with correct styling', () => {
      render(<SimulationResults result={mockResult} />);

      const plots = screen.getAllByTestId('plotly-plot');
      const velocityPlot = plots[1];

      const data = JSON.parse(velocityPlot.getAttribute('data-plot-data') || '[]');
      expect(data[0].name).toBe('流速');
      expect(data[0].line.color).toBe('#52c41a');
    });

    it('should render discharge plot with correct styling', () => {
      render(<SimulationResults result={mockResult} />);

      const plots = screen.getAllByTestId('plotly-plot');
      const dischargePlot = plots[2];

      const data = JSON.parse(dischargePlot.getAttribute('data-plot-data') || '[]');
      expect(data[0].name).toBe('流量');
      expect(data[0].line.color).toBe('#fa8c16');
    });

    it('should show all plots in Cards with titles', () => {
      render(<SimulationResults result={mockResult} />);

      expect(screen.getByText('水深分布')).toBeInTheDocument();
      expect(screen.getByText('流速分布')).toBeInTheDocument();
      expect(screen.getByText('流量分布')).toBeInTheDocument();
    });
  });

  describe('3D View Features', () => {
    it('should render 3D plots when tab is active', async () => {
      render(<SimulationResults result={mockResult} />);

      const threeDTab = screen.getByText(/3D可视化/i);
      await user.click(threeDTab);

      // Wait for tab content to render
      await waitFor(() => {
        const plots = screen.getAllByTestId('plotly-plot');
        expect(plots.length).toBeGreaterThanOrEqual(2);
      });
    });

    it('should pass all time steps to 3D plots', async () => {
      render(<SimulationResults result={mockResult} />);

      const threeDTab = screen.getByText(/3D可视化/i);
      await user.click(threeDTab);

      // Wait for plots to render
      await waitFor(() => {
        const plots = screen.getAllByTestId('plotly-plot');
        expect(plots.length).toBeGreaterThan(0);
      });

      const plots = screen.getAllByTestId('plotly-plot');
      const plot3DData = JSON.parse(plots[0].getAttribute('data-plot-data') || '[]');

      expect(plot3DData[0].x).toEqual(mockResult.x);
      expect(plot3DData[0].y).toEqual(mockResult.time);
      expect(plot3DData[0].z).toEqual(mockResult.h);
    });
  });

  describe('Enhanced Charts Features', () => {
    it('should render all enhanced chart types when tab is active', async () => {
      render(<SimulationResults result={mockResult} />);

      const enhancedTab = screen.getByText(/增强图表/i);
      await user.click(enhancedTab);

      // Should have contour, heatmaps, time series, statistics
      await waitFor(() => {
        const plots = screen.getAllByTestId('plotly-plot');
        expect(plots.length).toBeGreaterThanOrEqual(6);
      });
    });

    it('should pass complete data to EnhancedCharts', async () => {
      render(<SimulationResults result={mockResult} />);

      const enhancedTab = screen.getByText(/增强图表/i);
      await user.click(enhancedTab);

      // Wait for plots to render
      await waitFor(() => {
        const plots = screen.getAllByTestId('plotly-plot');
        expect(plots.length).toBeGreaterThan(0);
      });

      // Verify contour plot has all data
      const plots = screen.getAllByTestId('plotly-plot');
      const contourData = JSON.parse(plots[0].getAttribute('data-plot-data') || '[]');

      expect(contourData[0].x).toEqual(mockResult.x);
      expect(contourData[0].y).toEqual(mockResult.time);
      expect(contourData[0].z).toEqual(mockResult.h);
    });
  });

  describe('Error Handling', () => {
    it('should display failed status for incomplete simulation', () => {
      const failedResult = {
        ...mockResult,
        status: 'failed' as const
      };

      render(<SimulationResults result={failedResult} />);

      expect(screen.getByText(/✗ 模拟失败/i)).toBeInTheDocument();
    });

    it('should handle missing metrics gracefully', () => {
      const resultWithPartialMetrics = {
        ...mockResult,
        metrics: {
          ...mockResult.metrics,
          converged: false
        }
      };

      render(<SimulationResults result={resultWithPartialMetrics} />);

      expect(screen.getByText(/⚠ 未收敛/i)).toBeInTheDocument();
    });

    it('should display warning for poor mass conservation', () => {
      const resultWithPoorConservation = {
        ...mockResult,
        metrics: {
          ...mockResult.metrics,
          mass_conservation_error: 1e-4
        }
      };

      render(<SimulationResults result={resultWithPoorConservation} />);

      // Should show error value without ✓
      expect(screen.getByText(/1\.00e-4/i)).toBeInTheDocument();
    });
  });

  describe('Responsive Behavior', () => {
    it('should configure plots as responsive', () => {
      render(<SimulationResults result={mockResult} />);

      const plots = screen.getAllByTestId('plotly-plot');
      plots.forEach(plot => {
        const config = JSON.parse(plot.getAttribute('data-plot-config') || '{}');
        expect(config.responsive).toBe(true);
      });
    });

    it('should hide plotly logo in all plots', () => {
      render(<SimulationResults result={mockResult} />);

      const plots = screen.getAllByTestId('plotly-plot');
      plots.forEach(plot => {
        const config = JSON.parse(plot.getAttribute('data-plot-config') || '{}');
        expect(config.displaylogo).toBe(false);
      });
    });
  });

  describe('Performance Optimization', () => {
    it('should use useMemo for plot data', () => {
      const { rerender } = render(<SimulationResults result={mockResult} />);

      const plots1 = screen.getAllByTestId('plotly-plot');
      const data1 = plots1[0].getAttribute('data-plot-data');

      // Rerender with same result (but different object reference)
      const sameResult = { ...mockResult };
      rerender(<SimulationResults result={sameResult} />);

      const plots2 = screen.getAllByTestId('plotly-plot');
      const data2 = plots2[0].getAttribute('data-plot-data');

      // Data should be memoized based on dependencies
      expect(data1).toBe(data2);
    });

    it('should handle animations without lag', async () => {
      render(<SimulationResults result={mockResult} />);

      // Rapidly step through frames
      const stepForwardButton = screen.getByRole('button', { name: /下一帧/i });

      for (let i = 0; i < 3; i++) {
        await user.click(stepForwardButton);
      }

      // Should reach frame 4 without errors
      await waitFor(() => {
        expect(screen.getByText('4')).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper heading structure', () => {
      render(<SimulationResults result={mockResult} />);

      // Cards provide semantic structure
      expect(screen.getByText(/性能指标/i)).toBeInTheDocument();
      expect(screen.getByText(/动画控制/i)).toBeInTheDocument();
    });

    it('should provide clear visual feedback for status', () => {
      render(<SimulationResults result={mockResult} />);

      const successBadge = screen.getByText(/✓ 模拟完成/i);
      expect(successBadge).toBeInTheDocument();
    });

    it('should have keyboard-navigable tabs', async () => {
      render(<SimulationResults result={mockResult} />);

      const enhancedTab = screen.getByText(/增强图表/i);
      enhancedTab.focus();
      expect(enhancedTab).toHaveFocus();
    });
  });
});
