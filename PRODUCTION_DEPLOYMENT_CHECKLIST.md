# HydroClaude v1.4.2 生产环境部署检查清单
# Production Deployment Checklist

**版本**: v1.4.2
**目标环境**: 生产环境 (Production)
**部署日期**: ____________
**负责人**: ____________

---

## 📋 部署前检查 (Pre-Deployment)

### 1. 代码准备

- [ ] **代码审查完成**
  - 所有PR已合并
  - 代码符合规范
  - 无明显技术债务

- [ ] **版本标签**
  - Git tag创建: `v1.4.2`
  - CHANGELOG.md 更新
  - package.json版本号更新

- [ ] **分支状态**
  - 主分支代码最新
  - 无未合并的关键修复
  - 无冲突

### 2. 测试验证

- [ ] **单元测试** (必须)
  - 运行命令: `npm run test:run`
  - 通过率: 152/152 (100%)
  - 无失败用例

- [ ] **UAT测试** (必须)
  - 参考: `UAT_TEST_PLAN.md`
  - 35个测试用例执行
  - 通过率: ≥95%
  - 严重缺陷: 0个

- [ ] **浏览器兼容性** (必须)
  - 参考: `BROWSER_COMPATIBILITY_MATRIX.md`
  - Chrome, Firefox, Safari测试通过
  - Edge测试通过 (推荐)
  - 移动端测试通过 (推荐)

- [ ] **性能测试** (推荐)
  - FCP < 1.5s
  - LCP < 2.5s
  - TTI < 3.5s
  - 动画FPS > 20

- [ ] **安全扫描** (推荐)
  - `npm audit` 无高危漏洞
  - 依赖包安全检查
  - 环境变量不包含敏感信息

---

## 🔧 环境配置

### 3. 前端配置

- [ ] **环境变量配置**
  ```bash
  # .env.production (确保已创建)
  VITE_API_URL=https://api.hydroclaude.com  # 生产API地址
  VITE_API_TIMEOUT=30000
  VITE_ENABLE_SENTRY=true                   # 可选
  VITE_SENTRY_DSN=your-sentry-dsn          # 如果启用Sentry
  VITE_APP_VERSION=1.4.2
  VITE_APP_NAME=HydroClaude Web
  ```

- [ ] **构建验证**
  - 运行: `npm run build`
  - 构建成功，无错误
  - 检查dist目录生成
  - bundle大小合理 (<6MB总计)

- [ ] **代码分割验证**
  - 确认15个chunks生成
  - vendor-plotly正确分离
  - 初始加载bundle <1MB (gzipped)

### 4. 后端配置

- [ ] **API服务器**
  - 生产API地址确认
  - API版本兼容性检查
  - 健康检查端点测试

- [ ] **数据库** (如适用)
  - 数据库连接配置
  - 备份策略确认
  - 迁移脚本测试

- [ ] **CORS配置**
  - 前端域名加入白名单
  - 允许的HTTP方法配置
  - 凭证处理设置

---

## 🚀 部署配置

### 5. 服务器/托管

**选项A: 静态托管 (推荐前端)**

- [ ] **选择平台**
  - □ Netlify
  - □ Vercel
  - □ AWS S3 + CloudFront
  - □ Azure Static Web Apps
  - □ GitHub Pages
  - □ 其他: ____________

- [ ] **域名配置**
  - DNS记录设置
  - SSL证书配置 (HTTPS)
  - 自定义域名绑定

- [ ] **构建配置**
  - 构建命令: `npm run build`
  - 发布目录: `web/frontend/dist`
  - Node版本: 18+

**选项B: 容器化部署**

- [ ] **Docker配置**
  - Dockerfile创建
  - 镜像构建测试
  - 容器运行验证

- [ ] **编排工具** (如适用)
  - docker-compose.yml
  - Kubernetes manifests
  - 健康检查配置

### 6. CI/CD Pipeline

- [ ] **GitHub Actions** (或其他CI工具)
  ```yaml
  # .github/workflows/deploy-production.yml
  name: Deploy to Production
  on:
    push:
      tags:
        - 'v*'
  jobs:
    deploy:
      runs-on: ubuntu-latest
      steps:
        - Checkout code
        - Setup Node.js
        - Install dependencies
        - Run tests
        - Build
        - Deploy
  ```

- [ ] **自动化测试**
  - 单元测试在CI中运行
  - 代码质量检查
  - 构建成功验证

- [ ] **部署策略**
  - □ 蓝绿部署
  - □ 金丝雀发布
  - □ 滚动更新
  - □ 一次性部署

---

## 🔒 安全配置

### 7. 安全检查

- [ ] **HTTPS强制**
  - SSL/TLS证书有效
  - HTTP自动重定向到HTTPS
  - HSTS头配置

- [ ] **安全头配置**
  ```nginx
  # 示例 (Nginx)
  add_header X-Frame-Options "SAMEORIGIN";
  add_header X-Content-Type-Options "nosniff";
  add_header X-XSS-Protection "1; mode=block";
  add_header Referrer-Policy "strict-origin-when-cross-origin";
  add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';";
  ```

- [ ] **敏感信息保护**
  - .env文件不在版本控制中
  - API密钥安全存储
  - 生产环境日志脱敏

- [ ] **依赖安全**
  - `npm audit` 检查
  - 高危漏洞已修复
  - 依赖版本锁定 (package-lock.json)

---

## 📊 监控和日志

### 8. 错误追踪

- [ ] **Sentry集成** (推荐)
  ```bash
  npm install @sentry/react @sentry/vite-plugin
  ```
  - DSN配置
  - 环境标识 (production)
  - Release版本追踪
  - Source maps上传

- [ ] **日志配置**
  - logger.ts已集成
  - 生产环境日志级别: error, warn
  - 日志格式统一

### 9. 性能监控

- [ ] **Web Vitals追踪** (推荐)
  ```typescript
  import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';
  // 发送到分析服务
  ```

- [ ] **Analytics集成** (可选)
  - Google Analytics
  - Mixpanel
  - 自定义分析

- [ ] **性能预算**
  - Lighthouse CI配置
  - 性能基准设定
  - 自动化性能报告

---

## 🌐 CDN和缓存

### 10. 静态资源优化

- [ ] **CDN配置** (推荐)
  - 静态文件托管到CDN
  - vendor chunks使用CDN
  - 图片资源CDN加速

- [ ] **缓存策略**
  ```nginx
  # 示例缓存头
  location /assets/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
  }

  location / {
    expires -1;
    add_header Cache-Control "no-cache";
  }
  ```

- [ ] **压缩配置**
  - Gzip启用
  - Brotli启用 (如支持)
  - 压缩级别优化

---

## 📦 数据和备份

### 11. 数据管理

- [ ] **数据库备份** (如适用)
  - 自动备份策略
  - 备份存储位置
  - 恢复流程测试

- [ ] **静态文件备份**
  - 源代码版本控制
  - 构建产物归档
  - 配置文件备份

---

## 🔄 回滚计划

### 12. 应急预案

- [ ] **回滚流程**
  - 上一版本保留
  - 回滚命令准备
  - 回滚测试演练

- [ ] **故障处理**
  - 紧急联系人清单
  - 故障响应流程
  - 状态页面准备 (可选)

---

## ✅ 部署执行 (Deployment)

### 13. 部署步骤

**步骤1: 最终确认**
- [ ] 所有前置检查完成
- [ ] 团队成员知晓
- [ ] 时间窗口确定 (建议非高峰)

**步骤2: 备份**
- [ ] 当前版本代码备份
- [ ] 数据库快照 (如适用)
- [ ] 配置文件备份

**步骤3: 构建**
```bash
cd /path/to/HydroClaude/web/frontend
npm ci                    # 清洁安装依赖
npm run test:run         # 运行测试
npm run build            # 生产构建
```
- [ ] 构建成功
- [ ] 文件生成正确

**步骤4: 部署**
- [ ] 上传文件到服务器/平台
- [ ] 验证文件完整性
- [ ] 更新环境变量

**步骤5: 验证**
- [ ] 访问生产URL
- [ ] 首页加载正常
- [ ] 关键功能测试
  - [ ] 建模工作台
  - [ ] 仿真管理
  - [ ] 动画控制
  - [ ] 3D可视化

**步骤6: 监控**
- [ ] 检查错误日志
- [ ] 监控性能指标
- [ ] 观察用户反馈

---

## 📋 部署后检查 (Post-Deployment)

### 14. 验证清单

**功能验证**:
- [ ] 登录/认证功能 (如有)
- [ ] 核心业务流程
- [ ] 数据持久化
- [ ] API调用正常

**性能验证**:
- [ ] 首次加载 < 3s
- [ ] 页面响应迅速
- [ ] 动画流畅 (FPS > 20)
- [ ] 无内存泄漏

**兼容性验证**:
- [ ] Chrome浏览器
- [ ] Firefox浏览器
- [ ] Safari浏览器
- [ ] 移动端浏览器

**监控验证**:
- [ ] Sentry接收错误
- [ ] 日志正常输出
- [ ] Analytics数据采集

### 15. 文档更新

- [ ] **更新README.md**
  - 生产URL
  - 版本信息
  - 联系方式

- [ ] **更新CHANGELOG.md**
  - v1.4.2发布记录
  - 主要功能
  - 性能改进

- [ ] **通知相关方**
  - 团队成员
  - 利益相关者
  - 用户 (如适用)

---

## 📊 部署记录

### 部署信息

| 项目 | 信息 |
|------|------|
| **部署日期** | ____________ |
| **部署时间** | ____________ |
| **部署人员** | ____________ |
| **版本号** | v1.4.2 |
| **Git Commit** | ____________ |
| **环境** | Production |
| **部署方式** | □手动 □自动化 |

### 部署结果

| 检查项 | 状态 | 备注 |
|--------|------|------|
| 构建成功 | □是 □否 | |
| 部署成功 | □是 □否 | |
| 功能验证 | □通过 □失败 | |
| 性能验证 | □通过 □失败 | |
| 监控正常 | □是 □否 | |

### 问题记录

| 问题 | 严重程度 | 解决方案 | 状态 |
|------|----------|----------|------|
| | □致命 □严重 □一般 □轻微 | | □已解决 □待解决 |
| | □致命 □严重 □一般 □轻微 | | □已解决 □待解决 |

---

## 🎉 部署完成确认

**最终确认**:
- [ ] 所有检查项通过
- [ ] 无严重问题
- [ ] 监控正常运行
- [ ] 团队确认可用

**签署**:

**部署工程师**: ________________ 日期: ____________

**技术负责人**: ________________ 日期: ____________

**产品负责人**: ________________ 日期: ____________

---

## 📞 支持联系方式

### 技术支持

| 角色 | 姓名 | 联系方式 | 可用时间 |
|------|------|----------|----------|
| 技术负责人 | __________ | __________ | 24/7 |
| 部署工程师 | __________ | __________ | 工作时间 |
| 运维工程师 | __________ | __________ | 24/7 |

### 应急响应

**故障等级**:
- P0 (致命): 系统完全不可用 - 15分钟响应
- P1 (严重): 核心功能不可用 - 1小时响应
- P2 (一般): 部分功能问题 - 4小时响应
- P3 (轻微): 小问题或优化 - 1个工作日响应

**升级流程**:
1. 部署工程师
2. 技术负责人
3. CTO/技术总监

---

## 📚 参考文档

- `README.md` - 项目说明
- `NEXT_STEPS.md` - 后续计划
- `PROJECT_STATUS_2025_11_11_FINAL.md` - 项目状态
- `UAT_TEST_PLAN.md` - UAT测试
- `BROWSER_COMPATIBILITY_MATRIX.md` - 浏览器兼容性
- `PERFORMANCE_TESTING.md` - 性能测试

---

## 📝 附录

### A. 常见部署问题

**问题1: 构建失败**
```bash
# 解决方案
rm -rf node_modules package-lock.json
npm install
npm run build
```

**问题2: 环境变量未生效**
```bash
# 确保文件存在
ls -la .env.production

# 检查文件权限
chmod 644 .env.production
```

**问题3: 404错误**
```nginx
# Nginx配置 - SPA路由支持
location / {
  try_files $uri $uri/ /index.html;
}
```

### B. 性能优化建议

1. 启用HTTP/2
2. 配置CDN
3. 启用Brotli压缩
4. 设置合理的缓存策略
5. 使用预加载 (preload) 关键资源

### C. 监控指标

**关键指标**:
- 可用性 (Uptime): >99.9%
- 响应时间 (TTFB): <200ms
- 错误率: <0.1%
- FPS: >20
- 内存使用: <500MB

**告警阈值**:
- 可用性 <99%: P0告警
- 错误率 >1%: P1告警
- 响应时间 >1s: P2告警

---

**检查清单版本**: 1.0
**最后更新**: 2025-11-11
**维护者**: DevOps Team

---

*部署前请仔细检查每一项，确保安全稳定上线！* ✅
