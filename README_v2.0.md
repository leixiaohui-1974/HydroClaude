# HydroClaude v2.0.0

**一维水力学仿真软件 | 开源 | 跨平台 | 现代化GUI**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-green.svg)]()
[![Version](https://img.shields.io/badge/version-2.0.0-orange.svg)]()

---

## 📖 简介

HydroClaude是一款现代化的一维水力学仿真软件，提供图形化用户界面、专业可视化工具和GIS集成功能。适用于教学、科研和工程应用。

**主要特性**:
- 🎨 **现代化GUI** - React + Ant Design界面
- 🗺️ **GIS集成** - Leaflet地图和渠道绘制
- 🔌 **插件系统** - 8个标准API，可扩展
- 💻 **跨平台** - Windows、macOS、Linux
- 📊 **专业可视化** - 8种交互式图表
- 🔄 **自动更新** - 无缝升级体验

---

## 🚀 快速开始

### 桌面应用

#### Windows
```bash
# 下载并运行安装程序
HydroClaude-Setup-2.0.0.exe

# 或使用便携版
HydroClaude-2.0.0-portable.exe
```

#### macOS
```bash
# 下载并打开DMG文件
open HydroClaude-2.0.0.dmg
# 拖拽到Applications文件夹
```

#### Linux
```bash
# AppImage (通用)
chmod +x HydroClaude-2.0.0.AppImage
./HydroClaude-2.0.0.AppImage

# Debian/Ubuntu
sudo dpkg -i hydroclaude_2.0.0_amd64.deb

# Fedora/CentOS
sudo rpm -i hydroclaude-2.0.0.x86_64.rpm
```

---

### 开发模式

```bash
# 1. 克隆仓库
git clone https://github.com/hydroclaude/hydroclaude.git
cd hydroclaude

# 2. 安装Python依赖
pip install -r requirements.txt

# 3. 启动Web应用
cd webapp
npm install
npm run dev

# 4. 或启动桌面应用
npm run dev:electron
```

---

## 📚 文档

### 用户文档

- [快速开始](./docs/quick-start.md)
- [用户手册](./docs/user-manual.md)
- [使用教程](./docs/tutorials/)

### 开发文档

- [插件开发指南](./docs/plugins/getting-started.md)
- [API参考](./docs/plugins/api-reference.md)
- [桌面应用开发](./webapp/ELECTRON_README.md)
- [贡献指南](./CONTRIBUTING.md)

### 快速体验

- [Web应用快速体验](./🚀_Phase5.1_快速体验Web应用.md)
- [GIS功能快速体验](./🚀_Phase5.2_快速体验GIS功能.md)
- [插件系统快速体验](./🚀_Phase5.3_快速体验插件系统.md)
- [桌面应用快速体验](./🎉_Phase5.4_桌面应用_快速体验.md)

---

## 🎯 核心功能

### 1. 配置编辑

- **可视化编辑器** - 表单式参数设置
- **JSON编辑器** - 高级用户直接编辑
- **实时预览** - 即时查看配置效果
- **验证提示** - 实时参数验证

### 2. 仿真运行

- **单一入口** - `hydro_engine.py`统一接口
- **标准化I/O** - JSON、CSV、HDF5格式
- **进度监控** - 实时查看仿真进度
- **结果保存** - 多种格式导出

### 3. 结果可视化

**8种专业图表**:
- 📈 纵剖面图 - 水深沿程变化
- 📉 时间序列图 - 动态过程分析
- 🔄 相位图 - 流态分析
- 📊 弗劳德数图 - 临界流判断
- ✅ 流量验证图 - 质量守恒检查
- 🌈 3D曲面图 - 时空分布
- 📊 水力要素对比 - 多变量对比
- 📈 流态分析 - 统计分布

**交互功能**:
- 🖱️ 缩放和平移
- 📸 导出高清图片
- 📊 数据表格查看
- 🎬 动画播放

### 4. GIS集成

**地图功能**:
- 🗺️ 5种底图（街道、卫星、地形等）
- ✏️ 渠道绘制工具
- 📏 长度和坡度自动计算
- 📐 节点精确编辑
- 💾 GeoJSON导入导出

**结果叠加**:
- 🌊 水深颜色映射
- 💨 流速矢量场
- 🎨 5种色图方案
- 🔍 交互式查询

### 5. 插件系统

**8个标准API**:
- **Simulation API** - 仿真控制
- **Visualization API** - 可视化扩展
- **Data API** - 数据处理
- **UI API** - 用户界面
- **Utils API** - 工具函数
- **Storage API** - 数据存储
- **Events API** - 事件通信
- **Commands API** - 命令系统

**示例插件**:
- 🎯 参数优化插件
- 📥 数据导入插件
- 📊 自定义可视化插件

### 6. 桌面应用

**系统集成**:
- 📁 本地文件访问
- 🔔 系统托盘
- ⌨️ 快捷键支持
- 🍎 原生菜单

**自动更新**:
- 🔄 启动时检查
- 📥 后台下载
- 🔧 静默安装

---

## 🏗️ 技术架构

### 前端

```
React 18 + TypeScript
├── UI框架: Ant Design 5
├── 路由: React Router
├── 状态: Zustand
├── 可视化: Plotly.js
├── 地图: Leaflet
└── 构建: Vite
```

### 桌面

```
Electron 28
├── 打包: electron-builder
├── 开发: electron-vite
└── 更新: electron-updater
```

### 后端

```
Python 3.x
├── 数值计算: NumPy, SciPy
├── 可视化: Matplotlib
├── 数据处理: Pandas
└── 大数据: HDF5
```

---

## 📊 项目结构

```
hydroclaude/
├── webapp/                  # Web应用
│   ├── src/                 # React源代码
│   │   ├── pages/           # 页面组件
│   │   ├── components/      # 通用组件
│   │   ├── services/        # API服务
│   │   └── utils/           # 工具函数
│   ├── electron/            # Electron代码
│   │   ├── main/            # 主进程
│   │   └── preload/         # Preload脚本
│   └── public/              # 静态资源
│
├── solvers/                 # 求解器
├── utils/                   # 后端工具
├── docs/                    # 文档
│   └── plugins/             # 插件开发文档
├── plugins/                 # 插件
│   └── examples/            # 示例插件
└── examples/                # 使用示例
```

---

## 🎓 使用场景

### 教学

- ✅ 图形化界面，易于学习
- ✅ 直观的可视化
- ✅ 离线使用，教室演示
- ✅ 跨平台，学生自主安装

### 科研

- ✅ 专业的图表，论文插图
- ✅ 多种格式导出
- ✅ 插件扩展功能
- ✅ 开源透明，方法可验证

### 工程

- ✅ GIS集成，实际工程
- ✅ 快速建模
- ✅ 清晰的结果报告
- ✅ 免费使用

---

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

### 如何贡献

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

详见 [贡献指南](./CONTRIBUTING.md)

---

## 📝 许可证

本项目采用 [MIT许可证](./LICENSE)。

---

## 🔗 链接

- **GitHub**: https://github.com/hydroclaude/hydroclaude
- **文档**: https://docs.hydroclaude.com
- **问题反馈**: https://github.com/hydroclaude/hydroclaude/issues
- **讨论**: https://github.com/hydroclaude/hydroclaude/discussions

---

## 📧 联系方式

- **Email**: dev@hydroclaude.com
- **Twitter**: @hydroclaude
- **微信公众号**: HydroClaude

---

## 🎉 致谢

感谢所有为HydroClaude做出贡献的人！

特别感谢：
- Claude AI - 智能开发助手
- 开源社区 - 优秀的工具和库
- 早期用户 - 宝贵的反馈

---

## 📈 路线图

### v2.1.0 (计划中)
- [ ] 完善用户手册
- [ ] 更多示例案例
- [ ] 性能优化
- [ ] Bug修复

### v2.2.0 (计划中)
- [ ] 社区平台
- [ ] 插件市场后端
- [ ] 更多水工结构
- [ ] 参数灵敏度分析

### v3.0.0 (长期)
- [ ] 二维水力学
- [ ] 水质模拟
- [ ] AI/ML集成
- [ ] 云计算支持

---

<p align="center">
  <b>HydroClaude - 让水力学仿真更简单</b>
</p>

<p align="center">
  <i>开源 | 免费 | 现代化</i>
</p>
