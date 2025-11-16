/**
 * 自定义可视化插件
 * 
 * 功能：
 * - 热力图 (Heatmap)
 * - 等值线图 (Contour)
 * - 3D表面图 (3D Surface)
 * - 矢量场图 (Vector Field)
 * 
 * @author VizTeam
 * @version 1.0.0
 */

import type { Plugin, PluginAPI } from '../../../webapp/src/types/plugin';

/**
 * 热力图数据
 */
interface HeatmapData {
  x: number[];
  y: number[];
  z: number[][];
  colorscale?: string;
  title?: string;
}

/**
 * 等值线数据
 */
interface ContourData {
  x: number[];
  y: number[];
  z: number[][];
  contours?: {
    start?: number;
    end?: number;
    size?: number;
  };
  title?: string;
}

/**
 * 3D表面数据
 */
interface Surface3DData {
  x: number[];
  y: number[];
  z: number[][];
  colorscale?: string;
  title?: string;
}

/**
 * 自定义可视化插件类
 */
class CustomVisualizationPlugin implements Plugin {
  private api!: PluginAPI;

  manifest = {
    id: 'custom-visualization',
    name: '自定义可视化插件',
    version: '1.0.0',
    description: '添加新的图表类型',
    author: 'VizTeam',
    main: 'dist/index.js',
    permissions: [
      'visualization:read' as const,
      'visualization:create' as const,
      'data:read' as const,
      'ui:modify' as const,
    ],
    license: 'MIT',
  };

  /**
   * 插件激活
   */
  async onActivate(api: PluginAPI): Promise<void> {
    this.api = api;

    // 注册热力图
    api.visualization.registerChart({
      type: 'heatmap',
      component: this.createHeatmapComponent(),
      icon: 'heat',
      title: '热力图',
    });

    // 注册等值线图
    api.visualization.registerChart({
      type: 'contour',
      component: this.createContourComponent(),
      icon: 'contour',
      title: '等值线图',
    });

    // 注册3D表面图
    api.visualization.registerChart({
      type: 'surface3d',
      component: this.createSurface3DComponent(),
      icon: 'cube',
      title: '3D表面图',
    });

    // 注册命令
    api.commands.register('custom-viz.createHeatmap', () => this.createHeatmap());
    api.commands.register('custom-viz.createContour', () => this.createContour());
    api.commands.register('custom-viz.create3DSurface', () => this.create3DSurface());

    // 添加工具栏按钮
    api.ui.addButton({
      id: 'custom-viz-button',
      label: '自定义图表',
      icon: 'chart',
      position: 'toolbar',
      onClick: () => this.showChartMenu(),
    });

    // 监听仿真完成事件
    api.events.on('simulation:complete', (result) => {
      this.handleSimulationComplete(result);
    });

    api.utils.log('自定义可视化插件已激活');
  }

  /**
   * 插件停用
   */
  async onDeactivate(): Promise<void> {
    this.api.utils.log('自定义可视化插件已停用');
  }

  /**
   * 创建热力图
   */
  private async createHeatmap(): Promise<void> {
    try {
      // 获取数据
      const data = await this.getSimulationData();

      // 准备热力图数据
      const heatmapData: HeatmapData = {
        x: data.x,
        y: data.t,
        z: data.depth2d,
        colorscale: 'Viridis',
        title: '水深时空分布热力图',
      };

      // 创建图表
      this.api.visualization.createChart('heatmap', heatmapData);

      this.api.ui.showNotification({
        type: 'success',
        message: '热力图创建成功',
      });
    } catch (error) {
      this.api.utils.error('创建热力图失败:', error);
      this.api.ui.showNotification({
        type: 'error',
        message: '创建热力图失败',
      });
    }
  }

  /**
   * 创建等值线图
   */
  private async createContour(): Promise<void> {
    try {
      const data = await this.getSimulationData();

      const contourData: ContourData = {
        x: data.x,
        y: data.t,
        z: data.velocity2d,
        contours: {
          start: 0,
          end: 3,
          size: 0.2,
        },
        title: '流速等值线图',
      };

      this.api.visualization.createChart('contour', contourData);

      this.api.ui.showNotification({
        type: 'success',
        message: '等值线图创建成功',
      });
    } catch (error) {
      this.api.utils.error('创建等值线图失败:', error);
      this.api.ui.showNotification({
        type: 'error',
        message: '创建等值线图失败',
      });
    }
  }

  /**
   * 创建3D表面图
   */
  private async create3DSurface(): Promise<void> {
    try {
      const data = await this.getSimulationData();

      const surface3dData: Surface3DData = {
        x: data.x,
        y: data.t,
        z: data.surface2d,
        colorscale: 'Jet',
        title: '水面3D表面图',
      };

      this.api.visualization.createChart('surface3d', surface3dData);

      this.api.ui.showNotification({
        type: 'success',
        message: '3D表面图创建成功',
      });
    } catch (error) {
      this.api.utils.error('创建3D表面图失败:', error);
      this.api.ui.showNotification({
        type: 'error',
        message: '创建3D表面图失败',
      });
    }
  }

  /**
   * 显示图表菜单
   */
  private showChartMenu(): void {
    this.api.ui.showDialog({
      title: '选择图表类型',
      content: '请选择要创建的图表类型',
      onOk: () => {
        // 显示图表类型选择
      },
    });
  }

  /**
   * 获取仿真数据
   */
  private async getSimulationData(): Promise<any> {
    // 模拟数据
    const nx = 50;
    const nt = 20;

    const x = Array.from({ length: nx }, (_, i) => i * 20);
    const t = Array.from({ length: nt }, (_, i) => i * 100);

    // 生成2D数据
    const depth2d = Array.from({ length: nt }, (_, j) =>
      Array.from({ length: nx }, (_, i) => {
        const wave = Math.sin((i / nx) * Math.PI * 2 + (j / nt) * Math.PI);
        return 3.0 + 0.5 * wave;
      })
    );

    const velocity2d = Array.from({ length: nt }, (_, j) =>
      Array.from({ length: nx }, (_, i) => {
        const wave = Math.cos((i / nx) * Math.PI * 2 + (j / nt) * Math.PI);
        return 1.5 + 0.3 * wave;
      })
    );

    const surface2d = depth2d.map((row, j) =>
      row.map((h, i) => {
        const bed = (i / nx) * -0.5;
        return bed + h;
      })
    );

    return {
      x,
      t,
      depth2d,
      velocity2d,
      surface2d,
    };
  }

  /**
   * 创建热力图组件
   */
  private createHeatmapComponent(): any {
    // 返回一个React组件
    return function HeatmapChart({ data }: { data: HeatmapData }) {
      // 实际实现应该使用Plotly.js或其他图表库
      return `<div>热力图: ${data.title}</div>`;
    };
  }

  /**
   * 创建等值线图组件
   */
  private createContourComponent(): any {
    return function ContourChart({ data }: { data: ContourData }) {
      return `<div>等值线图: ${data.title}</div>`;
    };
  }

  /**
   * 创建3D表面图组件
   */
  private createSurface3DComponent(): any {
    return function Surface3DChart({ data }: { data: Surface3DData }) {
      return `<div>3D表面图: ${data.title}</div>`;
    };
  }

  /**
   * 处理仿真完成
   */
  private handleSimulationComplete(result: any): void {
    this.api.utils.log('仿真完成，可以创建自定义图表');

    // 自动创建热力图
    this.api.ui.showNotification({
      type: 'info',
      message: '仿真完成，可创建自定义图表',
    });
  }
}

// 导出插件实例
export default new CustomVisualizationPlugin();
