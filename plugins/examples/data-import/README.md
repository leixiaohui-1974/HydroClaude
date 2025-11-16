# Excel数据导入插件

**版本**: 2.0.0  
**作者**: Community Contributors  
**类别**: import-export

---

## 📖 概述

Excel数据导入插件支持从Excel、CSV、JSON等多种格式导入数据到HydroClaude，简化数据准备工作。

### 支持格式

- ✅ Excel (.xlsx, .xls)
- ✅ CSV (.csv)
- ✅ JSON (.json)
- ✅ TSV (.tsv)

---

## 🚀 快速开始

### 安装插件

1. 打开HydroClaude
2. 进入"插件市场"
3. 搜索"Excel数据导入"
4. 点击"安装"

### 导入数据

1. 点击工具栏"导入数据"按钮
2. 选择文件
3. 预览数据
4. 确认导入

---

## 🎯 功能详解

### 1. Excel导入

**支持功能**:
- 多工作表导入
- 自动检测表头
- 单元格格式识别
- 公式计算结果

**数据格式**:
```
| 参数名称 | 数值  | 单位 | 备注      |
|----------|-------|------|-----------|
| 糙率     | 0.025 | -    | Manning系数|
| 坡度     | 0.001 | -    | 底坡      |
| 宽度     | 10.0  | m    | 渠道宽度  |
```

### 2. CSV导入

**支持功能**:
- 自定义分隔符
- 引号处理
- 编码转换
- 空行跳过

**示例CSV**:
```csv
x,h,v,Fr
0.0,3.0,1.5,0.85
150.0,2.9,1.6,0.92
300.0,2.8,1.7,0.99
```

### 3. JSON导入

**支持格式**:

**数组格式**:
```json
[
  { "x": 0.0, "h": 3.0, "v": 1.5 },
  { "x": 150.0, "h": 2.9, "v": 1.6 }
]
```

**对象格式**:
```json
{
  "parameters": {
    "roughness": 0.025,
    "slope": 0.001,
    "width": 10.0
  }
}
```

---

## 📋 API使用

### 命令

#### 导入Excel
```typescript
await api.commands.execute('data-import.importExcel');
```

#### 导入CSV
```typescript
await api.commands.execute('data-import.importCSV');
```

#### 导入JSON
```typescript
await api.commands.execute('data-import.importJSON');
```

### 注册自定义导入器

```typescript
api.data.registerImporter({
  formats: ['txt'],
  handler: async (file: File) => {
    const content = await file.text();
    return parseMyFormat(content);
  }
});
```

---

## ⚙️ 配置选项

### 自动检测表头

```json
{
  "autoDetectHeaders": true
}
```

**说明**: 自动将第一行识别为表头

### 跳过空行

```json
{
  "skipEmptyRows": true
}
```

**说明**: 导入时忽略空行

### 文件编码

```json
{
  "encoding": "utf-8"
}
```

**选项**: utf-8, gbk, gb2312

---

## 📊 数据映射

### 标准映射

| 源字段 | 目标字段 | 类型 |
|--------|----------|------|
| x, distance, 距离 | position | number |
| h, depth, 水深 | depth | number |
| v, velocity, 流速 | velocity | number |
| Fr, froude | froude | number |

### 自定义映射

```typescript
const mapping = {
  '位置(m)': 'position',
  '水深(m)': 'depth',
  '流速(m/s)': 'velocity'
};

api.data.import(file, 'csv', { mapping });
```

---

## 🔧 高级用法

### 批量导入

```typescript
const files = [...]; // 文件数组

for (const file of files) {
  const result = await api.data.import(file, 'csv');
  console.log(`导入 ${file.name}: ${result.rowCount} 行`);
}
```

### 数据转换

```typescript
api.data.registerImporter({
  formats: ['csv'],
  handler: async (file: File) => {
    const raw = await parseCSV(file);
    
    // 数据转换
    const transformed = raw.map(row => ({
      x: parseFloat(row.position),
      h: parseFloat(row.depth),
      v: parseFloat(row.velocity)
    }));
    
    return transformed;
  }
});
```

### 数据验证

```typescript
function validateData(data: any[]): string[] {
  const errors: string[] = [];
  
  // 检查必需字段
  if (!data.every(row => 'x' in row)) {
    errors.push('缺少x字段');
  }
  
  // 检查数值范围
  if (data.some(row => row.h < 0)) {
    errors.push('水深不能为负');
  }
  
  return errors;
}
```

---

## 📈 性能

### 导入速度

| 文件大小 | 行数 | 时间 |
|----------|------|------|
| 100 KB   | ~1K  | < 1s |
| 1 MB     | ~10K | < 5s |
| 10 MB    | ~100K| < 30s|

### 内存使用

- **小文件** (< 1MB): ~10MB
- **中等文件** (1-10MB): ~50MB
- **大文件** (> 10MB): ~200MB

---

## 🐛 常见问题

### Q1: Excel文件打不开？

**A**:
- 检查文件是否损坏
- 确认文件格式（.xlsx / .xls）
- 尝试用Excel打开验证

### Q2: CSV乱码怎么办？

**A**:
- 检查文件编码
- 设置正确的编码格式
- 使用UTF-8编码保存

### Q3: 导入的数据不对？

**A**:
- 检查表头是否正确
- 验证数据类型
- 查看错误日志

### Q4: 大文件导入很慢？

**A**:
- 分批导入
- 关闭数据验证
- 使用CSV格式

---

## 📚 示例

### 示例1: 导入渠道几何

```typescript
// 准备Excel文件
// | x(m) | width(m) | depth(m) |
// | 0    | 10       | 0        |
// | 100  | 10       | 0        |
// | 200  | 10       | 0        |

const file = getExcelFile();
const result = await api.data.import(file, 'xlsx');

// 应用到配置
const config = await api.simulation.getConfig();
config.geometry = result.data;
await api.simulation.updateConfig(config);
```

### 示例2: 导入边界条件

```typescript
// CSV文件内容:
// time,flow,depth
// 0,10.0,3.0
// 3600,12.0,3.5
// 7200,15.0,4.0

const file = getCSVFile();
const result = await api.data.import(file, 'csv');

// 设置边界条件
const config = await api.simulation.getConfig();
config.boundary.upstream = result.data;
```

---

## 🔜 未来改进

- [ ] 支持更多格式（HDF5, NetCDF）
- [ ] 数据清洗功能
- [ ] 可视化数据预览
- [ ] 模板导入导出
- [ ] 批量处理
- [ ] 云端导入

---

## 📄 许可证

MIT License

---

<p align="center">
  <b>Excel数据导入插件 - 让数据导入更简单</b>
</p>
