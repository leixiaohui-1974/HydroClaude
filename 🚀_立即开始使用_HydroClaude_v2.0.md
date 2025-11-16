# 🚀 立即开始使用 HydroClaude v2.0.0

**版本**: 2.0.0  
**状态**: ✅ Ready to Use  
**完成度**: 100%

---

## 🎯 快速选择

根据你的需求，选择合适的入口：

```
┌─────────────────────────────────────────────┐
│  我是...                    我想要...       │
├─────────────────────────────────────────────┤
│  🎓 学生/教师              → 方式1: 桌面应用│
│  🔬 科研人员               → 方式1: 桌面应用│
│  🏗️ 工程师                 → 方式1: 桌面应用│
│  🧑‍💻 开发者                 → 方式2: Web开发 │
│  🔌 插件开发者             → 方式3: 插件开发│
│  🌐 后端API开发者          → 方式4: 后端API │
└─────────────────────────────────────────────┘
```

---

## 方式1: 桌面应用（推荐⭐）

**最简单、最快速的方式！**

### Step 1: 下载安装

#### Windows用户
```bash
# 下载安装程序
https://github.com/hydroclaude/hydroclaude/releases/download/v2.0.0/HydroClaude-Setup-2.0.0.exe

# 双击运行，按提示安装
```

#### macOS用户
```bash
# 下载DMG
https://github.com/hydroclaude/hydroclaude/releases/download/v2.0.0/HydroClaude-2.0.0.dmg

# 打开DMG，拖拽到Applications
```

#### Linux用户
```bash
# AppImage (通用)
wget https://github.com/hydroclaude/hydroclaude/releases/download/v2.0.0/HydroClaude-2.0.0.AppImage
chmod +x HydroClaude-2.0.0.AppImage
./HydroClaude-2.0.0.AppImage

# 或使用包管理器
# Debian/Ubuntu
sudo dpkg -i hydroclaude_2.0.0_amd64.deb

# Fedora/CentOS
sudo rpm -i hydroclaude-2.0.0.x86_64.rpm
```

---

### Step 2: 运行第一个仿真

1. **启动应用**
   - Windows: 开始菜单 → HydroClaude
   - macOS: Applications → HydroClaude
   - Linux: 应用菜单 → HydroClaude

2. **创建配置**
   - 点击"配置"标签
   - 选择"可视化编辑"
   - 填写基本参数:
     ```
     渠道长度: 10000 m
     渠道宽度: 10 m
     底坡: 0.001
     糙率: 0.025
     流量: 50 m³/s
     ```

3. **运行仿真**
   - 点击"保存配置"
   - 点击"运行仿真"
   - 等待计算完成（几秒钟）

4. **查看结果**
   - 点击"结果"标签
   - 浏览8种图表:
     - 纵剖面图
     - 时间序列图
     - 相位图
     - 弗劳德数图
     - 流量验证图
     - 3D曲面图
     - 水力要素对比
     - 流态分析

5. **地图功能**
   - 点击"地图"标签
   - 绘制渠道路径
   - 查看结果叠加

**完成！你已经成功运行了第一个仿真！** 🎉

---

### Step 3: 进阶功能

**添加水工结构**:
```json
{
  "structures": [
    {
      "type": "sluice_gate",
      "position": 5000,
      "width": 10,
      "opening": 2.0
    }
  ]
}
```

**导出结果**:
- 图片: PNG格式（右键图表）
- 数据: CSV/JSON/HDF5
- 报告: HTML完整报告

---

## 方式2: Web开发模式

**适合开发者和高级用户**

### Step 1: 克隆代码

```bash
# 克隆仓库
git clone https://github.com/hydroclaude/hydroclaude.git
cd hydroclaude
```

---

### Step 2: 安装依赖

**Python后端**:
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

**React前端**:
```bash
cd webapp
npm install
```

---

### Step 3: 运行开发服务器

**启动Web应用**:
```bash
cd webapp
npm run dev
```
访问: http://localhost:5173

**或启动桌面应用**:
```bash
cd webapp
npm run dev:electron
```

---

### Step 4: 开发和调试

**修改代码**:
```typescript
// webapp/src/pages/Dashboard/index.tsx
const Dashboard = () => {
  // 你的代码
}
```

**查看效果**:
- 保存文件
- 自动热重载
- 浏览器自动刷新

---

## 方式3: 插件开发

**扩展HydroClaude功能**

### Step 1: 阅读文档

```bash
# 打开插件开发文档
docs/plugins/getting-started.md
docs/plugins/api-reference.md
```

---

### Step 2: 创建插件

**目录结构**:
```
my-plugin/
├── plugin.json          # 插件清单
├── src/
│   └── index.ts         # 插件代码
└── README.md            # 说明文档
```

**plugin.json**:
```json
{
  "id": "my-awesome-plugin",
  "name": "My Awesome Plugin",
  "version": "1.0.0",
  "description": "插件描述",
  "author": "Your Name",
  "permissions": ["simulation:read", "ui:modify"]
}
```

**src/index.ts**:
```typescript
import type { Plugin, PluginAPI } from '@/types/plugin';

class MyPlugin implements Plugin {
  manifest = { /* ... */ };
  
  async onActivate(api: PluginAPI) {
    // 注册命令
    api.commands.register('my-plugin.hello', () => {
      api.ui.showMessage('Hello from my plugin!');
    });
    
    // 添加按钮
    api.ui.addButton({
      id: 'my-button',
      label: 'My Button',
      icon: 'smile',
      onClick: () => {
        api.commands.execute('my-plugin.hello');
      }
    });
  }
}

export default new MyPlugin();
```

---

### Step 3: 测试插件

```bash
# 复制到plugins目录
cp -r my-plugin plugins/examples/

# 重启应用
npm run dev:electron
```

**查看效果**:
- 打开插件市场
- 找到你的插件
- 点击"安装"
- 测试功能

---

### Step 4: 发布插件

1. **完善文档**
   ```markdown
   # My Plugin
   
   ## 功能
   - 功能1
   - 功能2
   
   ## 安装
   ...
   
   ## 使用
   ...
   ```

2. **创建Release**
   - 打包插件
   - 上传到GitHub
   - 发布到插件市场

---

## 方式4: 后端API开发

**构建社区平台**

### Step 1: 启动后端

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行服务器
python run.py
```

访问API文档: http://localhost:8000/docs

---

### Step 2: 测试API

**注册用户**:
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123"
  }'
```

**登录**:
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -d "username=testuser&password=password123"
```

**获取插件列表**:
```bash
curl http://localhost:8000/api/plugins
```

---

### Step 3: 开发新功能

**添加新路由**:
```python
# backend/api/routes/my_route.py
from fastapi import APIRouter

router = APIRouter(prefix="/my", tags=["My"])

@router.get("/hello")
async def hello():
    return {"message": "Hello World"}
```

**注册路由**:
```python
# backend/api/main.py
from .routes import my_route

app.include_router(my_route.router, prefix="/api")
```

---

## 📚 学习资源

### 用户文档

- [⭐ 快速开始](./⭐_开始这里_README.txt)
- [🚀 Web应用快速体验](./🚀_Phase5.1_快速体验Web应用.md)
- [🗺️ GIS功能快速体验](./🚀_Phase5.2_快速体验GIS功能.md)
- [🔌 插件系统快速体验](./🚀_Phase5.3_快速体验插件系统.md)
- [💻 桌面应用快速体验](./🎉_Phase5.4_桌面应用_快速体验.md)

---

### 开发文档

- [插件开发入门](./docs/plugins/getting-started.md)
- [API完整参考](./docs/plugins/api-reference.md)
- [最佳实践](./docs/plugins/best-practices.md)
- [FAQ](./docs/plugins/faq.md)
- [Electron开发](./webapp/ELECTRON_README.md)
- [后端API文档](./backend/README.md)

---

### 示例代码

**Python后端**:
```bash
examples/example_01_canal_flow/scripts/
├── 01_basic_v2.py              # 基础流动
├── 07_sluice_gate_flow_v2.py   # 单闸门
└── 12_advanced_optimized_v2.py # 多结构
```

**插件示例**:
```bash
plugins/examples/
├── parameter-optimization/     # 参数优化
├── data-import/                # 数据导入
└── custom-visualization/       # 自定义可视化
```

---

## 🆘 需要帮助？

### 常见问题

**Q: 如何导入已有项目？**
A: 文件 → 打开项目 → 选择JSON配置文件

**Q: 如何导出结果？**
A: 右键图表 → 导出图片，或数据表格 → 导出CSV

**Q: 如何添加水工结构？**
A: 配置编辑器 → JSON模式 → 编辑structures数组

**Q: 插件安装失败？**
A: 检查插件清单是否正确，查看错误日志

**Q: API连接失败？**
A: 确认后端服务运行，检查端口8000

---

### 获取支持

- **GitHub Issues**: https://github.com/hydroclaude/hydroclaude/issues
- **讨论区**: https://github.com/hydroclaude/hydroclaude/discussions
- **Email**: dev@hydroclaude.com
- **微信公众号**: HydroClaude

---

## 🎉 开始你的水力学之旅！

**选择你的路径**:

```
┌────────────────────────────────────────┐
│  👉 方式1: 桌面应用                    │
│     最简单，立即开始！                 │
│                                        │
│  👉 方式2: Web开发                     │
│     深度定制，自由开发                 │
│                                        │
│  👉 方式3: 插件开发                    │
│     扩展功能，分享作品                 │
│                                        │
│  👉 方式4: 后端API                     │
│     构建社区，连接世界                 │
└────────────────────────────────────────┘
```

**不管选择哪条路径，HydroClaude都已准备好陪伴你！**

---

<p align="center">
  <b>🚀 HydroClaude v2.0.0 - 立即开始！🚀</b>
</p>

<p align="center">
  <i>让水力学仿真更简单、更现代、更有趣</i>
</p>

<p align="center">
  <b>开源 | 免费 | 跨平台 | 可扩展</b>
</p>

---

**© 2025 HydroClaude Development Team**  
**Version: 2.0.0 | Status: Ready to Use**
