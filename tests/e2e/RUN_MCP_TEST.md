# 🚀 运行MCP完整端到端测试

## 前置条件

1. ✅ Node.js已安装 (v14+)
2. ✅ npm已安装
3. ✅ Puppeteer已安装
4. ✅ Web应用正在运行 (http://localhost:5173)

## 安装依赖

```bash
cd /workspace/tests/e2e

# 安装依赖
npm install

# 或者单独安装Puppeteer
npm install puppeteer
```

## 运行测试

### 测试所有111个案例

```bash
# 方式1: 使用npm脚本
npm run test:all

# 方式2: 直接运行
node mcp_full_test.js
```

### 测试部分案例

```bash
# 测试前5个案例
npm run test:5

# 测试前20个案例
npm run test:20
```

## 查看结果

### 截图

```
tests/e2e/screenshots_mcp_full/
├── case_001_xxx/
│   ├── 01_homepage.png
│   ├── 02_config_page.png
│   ├── 03_config_filled.png
│   ├── 04_submitted.png
│   ├── 05_computing.png
│   ├── 06_results_page.png
│   ├── 07_charts.png
│   └── 08_full_page.png
├── case_002_xxx/
└── ...
```

### 报告

```
tests/e2e/reports/
├── mcp_full_test_YYYYMMDD-HHMMSS.json  # JSON详细报告
└── mcp_full_test_YYYYMMDD-HHMMSS.html  # HTML可视化报告
```

在浏览器中打开HTML报告查看完整测试结果。

## 配置

编辑 `mcp_full_test.js` 中的 CONFIG 对象：

```javascript
const CONFIG = {
    baseUrl: 'http://localhost:5173',  // Web应用URL
    headless: true,                     // 无头模式
    timeout: 60000,                     // 超时时间(ms)
    maxCases: 111,                      // 测试案例数
};
```

## 故障排除

### 问题1: Puppeteer未安装

```bash
npm install puppeteer
```

### 问题2: Web应用未运行

```bash
cd /workspace/webapp
npm run dev
```

### 问题3: 测试超时

增加timeout配置值或检查Web应用响应速度。

