# HydroClaude Web 项目结构

> **更新日期**: 2025-11-12

## 📁 目录结构

\`\`\`
/workspace/web/
├── backend/                    # 后端代码
│   └── api_gateway/
│       ├── main.py            # 原始入口
│       ├── test_server.py     # 测试服务器（推荐）
│       ├── routers/           # 路由
│       ├── models/            # 数据模型
│       ├── shared/            # 共享代码
│       └── requirements.txt   # Python依赖
│
├── frontend/                   # 前端代码
│   ├── src/
│   │   ├── App.tsx           # 主应用
│   │   ├── features/
│   │   │   ├── modeling/     # 建模工作台
│   │   │   └── simulation/   # 仿真管理
│   │   ├── components/       # 公共组件
│   │   └── services/         # API服务
│   ├── package.json          # Node依赖
│   └── vite.config.ts        # Vite配置
│
├── test_scripts/              # 测试脚本
│   ├── ultimate_test.py      # ⭐ 终极测试
│   ├── comprehensive_test.py # 综合测试
│   ├── advanced_test.py      # 深度测试
│   └── ...
│
├── test_reports/              # 测试报告
│   ├── FINAL_COMPREHENSIVE_REPORT.md  # ⭐ 最终报告
│   ├── ISSUE_FIX_REPORT.md
│   └── *.json                # JSON报告
│
├── screenshots/               # 测试截图
│   ├── ultimate_screenshots/
│   ├── final_screenshots/
│   └── ...
│
├── scripts/                   # 工具脚本
│   ├── start_servers.sh      # 启动服务
│   ├── stop_servers.sh       # 停止服务
│   └── cleanup_tests.sh      # 清理测试
│
└── docs/                      # 文档
    ├── README.md
    ├── TEST_EXECUTION_GUIDE.md
    └── ...
\`\`\`

## 🔑 关键文件

### 后端

- **test_server.py**: 修复后的后端服务器，解决了sys.path问题
- **requirements.txt**: Python依赖列表

### 前端

- **App.tsx**: 主应用，包含建模工作台和仿真管理标签
- **ModelingWorkspace.tsx**: 建模工作台组件
- **SimulationWorkspace.tsx**: 仿真管理组件

### 测试

- **ultimate_test.py**: 最全面的测试脚本（推荐）
- **TEST_EXECUTION_GUIDE.md**: 测试执行指南

### 报告

- **FINAL_COMPREHENSIVE_REPORT.md**: 最终综合测试报告
- **ultimate_test_report.json**: JSON格式测试结果

## 🚀 快速开始

\`\`\`bash
# 1. 启动服务
cd /workspace/web
./start_servers.sh

# 2. 运行测试
python3 ultimate_test.py

# 3. 查看结果
cat FINAL_COMPREHENSIVE_REPORT.md
\`\`\`

## 📊 测试产物

测试执行后会生成：

- **JSON报告**: \`*_test_report.json\`
- **Markdown报告**: \`*_REPORT.md\`
- **截图**: \`*_screenshots/\` 目录

## 🧹 清理

\`\`\`bash
# 交互式清理
./cleanup_tests.sh

# 或手动清理
rm -rf *_screenshots/
rm -f *test_report.json
\`\`\`
