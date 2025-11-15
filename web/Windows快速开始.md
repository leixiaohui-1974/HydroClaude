# Windows 中文环境快速开始指南

## 🎯 目标

在 Windows 中文环境下完整测试 HydroClaude Web 系统的所有功能。

---

## 📋 系统要求

### 必需软件
- ✅ **Python 3.8+** (推荐 3.10 或 3.11)
- ✅ **Node.js 16+** (推荐 LTS 版本)
- ✅ **Git**

### 推荐配置
- Windows 10/11
- 内存: 8GB+
- 硬盘: 2GB+ 可用空间

---

## 🚀 快速开始 (5分钟)

### 步骤 1: 检查环境

打开 **命令提示符** 或 **PowerShell**，检查环境:

```cmd
python --version
node --version
npm --version
git --version
```

### 步骤 2: 克隆代码 (如果还没有)

```cmd
git clone <your-repo-url>
cd HydroClaude\web
```

### 步骤 3: 启动后端

方式一：双击运行
```
双击文件: backend\启动后端_Windows.bat
```

方式二：命令行运行
```cmd
cd backend
启动后端_Windows.bat
```

等待看到：
```
✅ 服务器启动成功
   API文档: http://localhost:8000/api/docs
```

### 步骤 4: 运行测试

**保持后端运行**，打开新的命令行窗口：

```cmd
cd web
python Windows中文环境测试脚本.py
```

---

## 📖 详细步骤

### 一、安装依赖

#### 后端依赖

```cmd
cd backend
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

主要包：
- fastapi
- uvicorn[standard]
- pydantic
- numpy
- matplotlib

#### 前端依赖

```cmd
cd frontend
npm install
```

### 二、启动服务

#### 启动后端 (端口 8000)

```cmd
cd backend
启动后端_Windows.bat
```

服务启动后可访问：
- **API文档**: http://localhost:8000/api/docs
- **健康检查**: http://localhost:8000/health
- **ReDoc**: http://localhost:8000/api/redoc

#### 启动前端 (端口 3000)

新开命令行窗口：

```cmd
cd frontend
npm run dev
```

访问: http://localhost:3000

### 三、运行测试

#### 后端API测试

```cmd
cd web
python Windows中文环境测试脚本.py
```

测试内容：
- ✅ 后端服务健康检查
- ✅ 中文名称仿真任务
- ✅ 任务状态查询
- ✅ 结果获取
- ✅ 列表API

#### 前端E2E测试 (需要安装 Playwright)

```cmd
cd web
pip install playwright
playwright install chromium

python comprehensive_e2e_test.py
```

---

## 🔍 测试验证清单

### 后端测试

| 功能 | 测试方法 | 预期结果 |
|------|---------|---------|
| 服务启动 | 访问 `/health` | 返回 200 |
| 中文支持 | 提交中文名称任务 | 正常接受和显示 |
| 仿真计算 | 提交标准测试用例 | 收敛，质量守恒误差 < 0.001% |
| 任务管理 | 查询任务列表 | 返回所有任务 |

### 前端测试

| 功能 | 测试方法 | 预期结果 |
|------|---------|---------|
| 界面加载 | 访问首页 | 正常显示导航栏和标签页 |
| 中文显示 | 查看所有文本 | 中文正确显示，无乱码 |
| 建模工作台 | 创建新案例 | 可输入参数 |
| 仿真管理 | 提交任务 | 显示进度 |
| 结果可视化 | 查看图表 | 图表正确渲染 |

---

## 🐛 常见问题

### 1. 中文乱码

**问题**: 控制台或日志出现乱码

**解决**:
```cmd
chcp 65001
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
```

或使用提供的 `启动后端_Windows.bat`，已自动配置。

### 2. 模块未找到

**问题**: `ModuleNotFoundError: No module named 'xxx'`

**解决**:
```cmd
pip install -r backend\requirements.txt
```

### 3. 端口被占用

**问题**: `Address already in use`

**解决**:

查找占用端口的进程：
```cmd
netstat -ano | findstr :8000
```

结束进程：
```cmd
taskkill /PID <进程ID> /F
```

### 4. 前端无法连接后端

**问题**: 前端报错 `Failed to fetch`

**检查**:
1. 后端是否运行: 访问 http://localhost:8000/health
2. 前端配置: 检查 `frontend/.env` 中 `VITE_API_URL`
3. CORS设置: 检查后端 `main.py` 中的 CORS 配置

### 5. npm 安装慢

**解决**: 使用国内镜像

```cmd
npm config set registry https://registry.npmmirror.com
npm install
```

---

## 📊 测试报告

测试脚本会自动生成报告，包括：

- 测试用例总数
- 通过/失败数量
- 成功率
- 详细错误信息

示例输出：

```
═══════════════════════════════════════════════════════════
  测试总结
═══════════════════════════════════════════════════════════

总测试数: 3
通过: 3 ✅
失败: 0 ❌
成功率: 100.0%

═══════════════════════════════════════════════════════════
✅ 🎉 所有测试通过！
═══════════════════════════════════════════════════════════
```

---

## 📸 截图验证

### 手动测试（用浏览器）

1. **后端 API 文档**
   - 访问: http://localhost:8000/api/docs
   - 截图: Swagger UI 界面

2. **前端界面**
   - 访问: http://localhost:3000
   - 截图: 主界面、建模工作台、仿真管理、结果展示

3. **中文测试**
   - 创建中文名称的案例
   - 截图: 确认中文正确显示

---

## 🎨 标准化模板

### 图表模板

系统使用标准化的图表模板，详见 `STANDARD_VISUALIZATION_TEMPLATES.md`：

1. **水面线图** - 蓝色主题
2. **水深图** - 青色主题
3. **流速图** - 绿色主题
4. **Froude数图** - 橙色主题
5. **流量图** - 紫色主题

### 表格模板

1. **配置参数表**
2. **统计指标表**
3. **关键位置表**
4. **结构参数表**

---

## 🔧 开发调试

### 查看日志

后端日志会输出到控制台，包括：
- 请求信息
- 错误堆栈
- 仿真进度

前端日志：
- 浏览器控制台 (F12)
- Network 标签查看API请求

### 调试模式

后端（开启热重载）：
```cmd
cd backend\api_gateway
uvicorn main:app --reload
```

前端（开发模式）：
```cmd
cd frontend
npm run dev
```

---

## 📞 获取帮助

### 资源文档

- `README.md` - 项目总体说明
- `WEB_SYSTEM_TESTING_GUIDE.md` - 系统测试指南
- `STANDARD_VISUALIZATION_TEMPLATES.md` - 标准化模板
- `API_SPECIFICATION.md` - API 详细规范

### 问题排查

1. 查看日志输出
2. 检查网络请求 (F12 Network)
3. 验证配置文件
4. 重启服务

---

## ✅ 测试完成标准

### 必须达成

- [x] 后端服务正常启动
- [x] 所有API端点响应正常
- [x] 中文字符正确显示（无乱码）
- [x] 仿真计算正确（质量守恒误差 < 0.001%）
- [x] 前端界面加载正常
- [x] 所有功能模块可访问

### 加分项

- [ ] E2E测试全部通过
- [ ] 性能测试达标
- [ ] 截图文档完整
- [ ] 错误处理优雅

---

## 🎉 完成！

完成上述测试后，系统即可在 Windows 中文环境下正常使用！

**生成日期**: 2025-11-15  
**版本**: 1.0  
**作者**: HydroClaude Development Team
