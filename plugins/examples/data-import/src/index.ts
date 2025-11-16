/**
 * 数据导入插件
 * 
 * 功能：
 * - 从Excel文件导入数据
 * - 从CSV文件导入数据
 * - 从JSON文件导入数据
 * - 自动检测数据格式
 * - 数据预览和验证
 * 
 * @author Community Contributors
 * @version 2.0.0
 */

import type { Plugin, PluginAPI } from '../../../webapp/src/types/plugin';

/**
 * 导入选项
 */
interface ImportOptions {
  autoDetectHeaders: boolean;
  skipEmptyRows: boolean;
  encoding: string;
}

/**
 * 导入结果
 */
interface ImportResult {
  data: any[];
  headers: string[];
  rowCount: number;
  columnCount: number;
  errors: string[];
}

/**
 * 数据导入插件类
 */
class DataImportPlugin implements Plugin {
  private api!: PluginAPI;

  manifest = {
    id: 'data-import-excel',
    name: 'Excel数据导入插件',
    version: '2.0.0',
    description: '从Excel、CSV、JSON等格式导入数据',
    author: 'Community Contributors',
    main: 'dist/index.js',
    permissions: [
      'data:read' as const,
      'data:write' as const,
      'ui:modify' as const,
      'filesystem:read' as const,
      'storage:write' as const,
    ],
    license: 'MIT',
  };

  /**
   * 插件激活
   */
  async onActivate(api: PluginAPI): Promise<void> {
    this.api = api;

    // 注册命令
    api.commands.register('data-import.importExcel', () => this.importExcel());
    api.commands.register('data-import.importCSV', () => this.importCSV());
    api.commands.register('data-import.importJSON', () => this.importJSON());

    // 注册数据导入器
    api.data.registerImporter({
      formats: ['xlsx', 'xls'],
      handler: (file) => this.handleExcelImport(file),
    });

    api.data.registerImporter({
      formats: ['csv'],
      handler: (file) => this.handleCSVImport(file),
    });

    api.data.registerImporter({
      formats: ['json'],
      handler: (file) => this.handleJSONImport(file),
    });

    // 添加工具栏按钮
    api.ui.addButton({
      id: 'import-button',
      label: '导入数据',
      icon: 'upload',
      position: 'toolbar',
      onClick: () => this.showImportDialog(),
    });

    api.utils.log('数据导入插件已激活');
  }

  /**
   * 插件停用
   */
  async onDeactivate(): Promise<void> {
    this.api.utils.log('数据导入插件已停用');
  }

  /**
   * 显示导入对话框
   */
  private showImportDialog(): void {
    this.api.ui.showDialog({
      title: '导入数据',
      content: '请选择要导入的文件类型',
      onOk: () => {
        // 显示文件选择器
        this.selectFile();
      },
    });
  }

  /**
   * 选择文件
   */
  private selectFile(): void {
    // 创建文件输入元素
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.xlsx,.xls,.csv,.json';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        await this.importFile(file);
      }
    };
    input.click();
  }

  /**
   * 导入文件
   */
  private async importFile(file: File): Promise<void> {
    const extension = file.name.split('.').pop()?.toLowerCase();

    try {
      this.api.ui.showNotification({
        type: 'info',
        message: `正在导入 ${file.name}...`,
      });

      let result: ImportResult;

      switch (extension) {
        case 'xlsx':
        case 'xls':
          result = await this.handleExcelImport(file);
          break;
        case 'csv':
          result = await this.handleCSVImport(file);
          break;
        case 'json':
          result = await this.handleJSONImport(file);
          break;
        default:
          throw new Error(`不支持的文件格式: ${extension}`);
      }

      // 显示导入结果
      this.showImportResult(result);

      this.api.ui.showNotification({
        type: 'success',
        message: `成功导入 ${result.rowCount} 行数据`,
      });
    } catch (error) {
      this.api.utils.error('导入失败:', error);
      this.api.ui.showNotification({
        type: 'error',
        message: '导入失败: ' + (error as Error).message,
      });
    }
  }

  /**
   * 导入Excel
   */
  private async importExcel(): Promise<void> {
    this.selectFile();
  }

  /**
   * 导入CSV
   */
  private async importCSV(): Promise<void> {
    this.selectFile();
  }

  /**
   * 导入JSON
   */
  private async importJSON(): Promise<void> {
    this.selectFile();
  }

  /**
   * 处理Excel导入
   */
  private async handleExcelImport(file: File): Promise<ImportResult> {
    const options = await this.getImportOptions();

    // 读取文件内容
    const content = await this.api.utils.readFile(file);

    // 解析Excel (简化版本，实际需要使用xlsx库)
    const data = this.parseExcelSimulated(content as string, options);

    // 验证数据
    const errors = this.validateData(data);

    return {
      data: data.rows,
      headers: data.headers,
      rowCount: data.rows.length,
      columnCount: data.headers.length,
      errors,
    };
  }

  /**
   * 处理CSV导入
   */
  private async handleCSVImport(file: File): Promise<ImportResult> {
    const options = await this.getImportOptions();

    // 读取文件内容
    const content = await this.api.utils.readFile(file);

    // 解析CSV
    const data = this.parseCSV(content as string, options);

    // 验证数据
    const errors = this.validateData(data);

    return {
      data: data.rows,
      headers: data.headers,
      rowCount: data.rows.length,
      columnCount: data.headers.length,
      errors,
    };
  }

  /**
   * 处理JSON导入
   */
  private async handleJSONImport(file: File): Promise<ImportResult> {
    // 读取文件内容
    const content = await this.api.utils.readFile(file);

    // 解析JSON
    const data = JSON.parse(content as string);

    // 转换为标准格式
    const normalized = this.normalizeJSONData(data);

    // 验证数据
    const errors = this.validateData(normalized);

    return {
      data: normalized.rows,
      headers: normalized.headers,
      rowCount: normalized.rows.length,
      columnCount: normalized.headers.length,
      errors,
    };
  }

  /**
   * 获取导入选项
   */
  private async getImportOptions(): Promise<ImportOptions> {
    return {
      autoDetectHeaders: (await this.api.storage.get('autoDetectHeaders')) ?? true,
      skipEmptyRows: (await this.api.storage.get('skipEmptyRows')) ?? true,
      encoding: (await this.api.storage.get('encoding')) || 'utf-8',
    };
  }

  /**
   * 解析Excel（模拟版本）
   */
  private parseExcelSimulated(
    content: string,
    options: ImportOptions
  ): { headers: string[]; rows: any[] } {
    // 实际实现需要使用xlsx库
    // 这里是简化的模拟实现
    const lines = content.split('\n').filter((line) => line.trim());

    if (lines.length === 0) {
      return { headers: [], rows: [] };
    }

    // 提取表头
    const headers = options.autoDetectHeaders
      ? lines[0].split('\t')
      : Array.from({ length: lines[0].split('\t').length }, (_, i) => `Column${i + 1}`);

    // 解析数据行
    const startRow = options.autoDetectHeaders ? 1 : 0;
    const rows = lines.slice(startRow).map((line) => {
      const values = line.split('\t');
      const row: any = {};
      headers.forEach((header, i) => {
        row[header] = values[i] || '';
      });
      return row;
    });

    return { headers, rows };
  }

  /**
   * 解析CSV
   */
  private parseCSV(content: string, options: ImportOptions): { headers: string[]; rows: any[] } {
    const lines = content.split('\n').filter((line) => {
      return !options.skipEmptyRows || line.trim();
    });

    if (lines.length === 0) {
      return { headers: [], rows: [] };
    }

    // 提取表头
    const headers = options.autoDetectHeaders
      ? this.parseCSVLine(lines[0])
      : Array.from({ length: this.parseCSVLine(lines[0]).length }, (_, i) => `Column${i + 1}`);

    // 解析数据行
    const startRow = options.autoDetectHeaders ? 1 : 0;
    const rows = lines.slice(startRow).map((line) => {
      const values = this.parseCSVLine(line);
      const row: any = {};
      headers.forEach((header, i) => {
        row[header] = values[i] || '';
      });
      return row;
    });

    return { headers, rows };
  }

  /**
   * 解析CSV行
   */
  private parseCSVLine(line: string): string[] {
    const values: string[] = [];
    let current = '';
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
      const char = line[i];

      if (char === '"') {
        inQuotes = !inQuotes;
      } else if (char === ',' && !inQuotes) {
        values.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }

    values.push(current.trim());
    return values;
  }

  /**
   * 规范化JSON数据
   */
  private normalizeJSONData(data: any): { headers: string[]; rows: any[] } {
    if (Array.isArray(data)) {
      // 数组格式
      if (data.length === 0) {
        return { headers: [], rows: [] };
      }

      // 提取所有键作为表头
      const headersSet = new Set<string>();
      data.forEach((row) => {
        Object.keys(row).forEach((key) => headersSet.add(key));
      });

      const headers = Array.from(headersSet);
      return { headers, rows: data };
    } else if (typeof data === 'object') {
      // 对象格式，转换为数组
      const headers = Object.keys(data);
      const rows = [data];
      return { headers, rows };
    }

    throw new Error('不支持的JSON格式');
  }

  /**
   * 验证数据
   */
  private validateData(data: { headers: string[]; rows: any[] }): string[] {
    const errors: string[] = [];

    // 检查表头
    if (data.headers.length === 0) {
      errors.push('未检测到表头');
    }

    // 检查数据行
    if (data.rows.length === 0) {
      errors.push('未检测到数据行');
    }

    // 检查数据完整性
    data.rows.forEach((row, i) => {
      data.headers.forEach((header) => {
        if (row[header] === undefined || row[header] === null) {
          errors.push(`第${i + 1}行缺少列"${header}"`);
        }
      });
    });

    return errors;
  }

  /**
   * 显示导入结果
   */
  private showImportResult(result: ImportResult): void {
    this.api.utils.log('导入结果:');
    this.api.utils.log(`- 行数: ${result.rowCount}`);
    this.api.utils.log(`- 列数: ${result.columnCount}`);
    this.api.utils.log(`- 表头: ${result.headers.join(', ')}`);

    if (result.errors.length > 0) {
      this.api.utils.warn('发现错误:');
      result.errors.forEach((error) => this.api.utils.warn(`- ${error}`));
    }

    // 预览前5行
    this.api.utils.log('数据预览:');
    result.data.slice(0, 5).forEach((row, i) => {
      this.api.utils.log(`行${i + 1}:`, row);
    });
  }
}

// 导出插件实例
export default new DataImportPlugin();
