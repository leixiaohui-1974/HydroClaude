/**
 * Playwright 配置文件
 * 
 * HydroClaude 前端测试配置
 * 按照 Spec-Kit 规范编写
 * 
 * Author: HydroClaude Test Team
 * Date: 2025-11-20
 * Spec: 001-comprehensive-review-and-testing
 */

const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  // 测试目录
  testDir: './tests/frontend',
  
  // 测试匹配模式
  testMatch: '**/*.spec.js',
  
  // 超时设置
  timeout: 30 * 1000,
  expect: {
    timeout: 5000
  },
  
  // 失败时重试
  retries: process.env.CI ? 2 : 0,
  
  // 并行worker数
  workers: process.env.CI ? 1 : undefined,
  
  // 报告生成器
  reporter: [
    ['html', { outputFolder: 'reports/html/playwright' }],
    ['json', { outputFile: 'reports/playwright-results.json' }],
    ['list']
  ],
  
  // 全局配置
  use: {
    // 基础 URL
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    
    // 截图
    screenshot: 'only-on-failure',
    
    // 视频
    video: 'retain-on-failure',
    
    // 追踪
    trace: 'retain-on-failure',
    
    // 视口大小
    viewport: { width: 1280, height: 720 },
    
    // 忽略 HTTPS 错误
    ignoreHTTPSErrors: true,
    
    // 等待超时
    actionTimeout: 10000,
    navigationTimeout: 30000,
  },
  
  // 测试项目配置
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    // 移动设备测试
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],
  
  // Web 服务器配置
  webServer: {
    command: 'npm run start',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});
