# ❓ HydroClaude 常见问题解答 (FAQ)

**版本**: 2.0.0  
**更新日期**: 2025-11-15

---

## 📋 目录

- [安装与设置](#安装与设置)
- [基础使用](#基础使用)
- [功能问题](#功能问题)
- [技术问题](#技术问题)
- [开发相关](#开发相关)
- [性能优化](#性能优化)
- [故障排除](#故障排除)

---

## 安装与设置

### Q1: 支持哪些操作系统？

**A**: HydroClaude支持以下操作系统：

- **Windows**: Windows 10及以上
- **macOS**: macOS 10.13 (High Sierra)及以上
- **Linux**: 
  - Ubuntu 18.04+
  - Fedora 32+
  - Debian 10+
  - 其他现代Linux发行版（通过AppImage）

---

### Q2: 如何安装HydroClaude？

**A**: 

**方式1: 桌面应用（推荐）**

1. 访问 [GitHub Releases](https://github.com/hydroclaude/hydroclaude/releases)
2. 下载适合你系统的安装包
3. 双击安装

**方式2: 从源码**

```bash
git clone https://github.com/hydroclaude/hydroclaude.git
cd hydroclaude/webapp
npm install
npm run dev:electron
```

---

### Q3: 安装包多大？

**A**: 

- Windows安装程序: ~80MB
- macOS DMG: ~85MB
- Linux AppImage: ~85MB

首次启动后总共占用约150-200MB磁盘空间。

---

### Q4: 需要安装Python吗？

**A**: 

- **桌面应用**: 不需要，所有依赖已打包
- **从源码运行**: 需要Python 3.11+（用于后端API，可选）

---

### Q5: 为什么启动很慢？

**A**: 

首次启动可能需要2-5秒，这是正常的。原因：
- Electron加载
- React应用初始化
- 检查更新

后续启动会更快（< 2秒）。

**优化建议**:
- 关闭不必要的启动项
- 使用SSD硬盘
- 确保有足够内存（建议4GB+）

---

## 基础使用

### Q6: 如何创建第一个仿真？

**A**: 

1. 启动HydroClaude
2. 点击"配置"标签
3. 选择"可视化编辑"模式
4. 填写基本参数:
   - 渠道长度: 10000 m
   - 渠道宽度: 10 m
   - 底坡: 0.001
   - 糙率: 0.025
   - 流量: 50 m³/s
5. 点击"运行仿真"
6. 查看结果

---

### Q7: 配置文件保存在哪里？

**A**: 

**桌面应用**:
- Windows: `C:\Users\用户名\Documents\HydroClaude\`
- macOS: `~/Documents/HydroClaude/`
- Linux: `~/Documents/HydroClaude/`

可以在"文件 → 打开项目"中查看和管理。

---

### Q8: 如何导出结果？

**A**: 

**导出图表**:
1. 进入"结果"页面
2. 右键点击任意图表
3. 选择"下载图片"或"导出数据"

**导出格式**:
- 图片: PNG (高分辨率)
- 数据: CSV, JSON, HDF5

**批量导出**:
- 点击"导出全部"按钮
- 选择导出格式和位置

---

### Q9: 支持哪些单位制？

**A**: 

目前使用**国际单位制(SI)**:
- 长度: 米(m)
- 时间: 秒(s)
- 流量: 立方米/秒(m³/s)
- 流速: 米/秒(m/s)

**未来计划**: v2.2.0将支持单位转换。

---

### Q10: 可以模拟多长时间？

**A**: 

- **稳态**: 无时间限制，直到收敛
- **非稳态**: 理论上无限制，但建议< 10000秒

实际限制取决于:
- 网格数量
- 时间步长
- 计算机性能

典型仿真时间: 几秒到几分钟。

---

## 功能问题

### Q11: 支持哪些水工结构？

**A**: 

目前支持:
- ✅ 闸门 (Sluice Gate)
- ✅ 堰 (Weir)
- ✅ 孔口 (Orifice)

**添加方法**:
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

**未来计划**: v2.2.0将增加更多结构类型。

---

### Q12: 如何绘制复杂的渠道形状？

**A**: 

1. 进入"地图"页面
2. 选择"渠道绘制"工具
3. 点击地图绘制路径
4. 编辑节点调整形状
5. 自动计算长度和坡度
6. 导出GeoJSON

**限制**: 目前仅支持矩形断面。

**未来计划**: v2.5.0将支持复杂断面。

---

### Q13: GIS地图需要联网吗？

**A**: 

- **在线地图**: 需要联网（OpenStreetMap等）
- **离线使用**: 可以使用缓存的瓦片

**建议**: 首次使用时联网缓存地图，之后可离线使用。

---

### Q14: 如何安装插件？

**A**: 

**方式1: 从插件市场（未来）**
1. 进入"插件"页面
2. 浏览或搜索插件
3. 点击"安装"

**方式2: 手动安装**
1. 下载插件文件夹
2. 复制到 `plugins/` 目录
3. 重启应用
4. 在"插件"页面激活

---

### Q15: 可以自定义图表样式吗？

**A**: 

**内置选项**:
- 颜色主题
- 线条样式
- 标记类型

**高级定制**:
- 开发自定义可视化插件
- 参考: `plugins/examples/custom-visualization/`

---

## 技术问题

### Q16: 使用什么数值方法？

**A**: 

HydroClaude提供两种求解器:

**1. HydrostaticCanalSolver (推荐)**
- 方法: 静水压力假设
- 优点: 快速、稳定
- 适用: 稳态和缓变流
- 误差: < 0.01%

**2. GodunvFVMSolver**
- 方法: Godunov有限体积法
- 优点: 通用、精确
- 适用: 非稳态和激波
- 误差: < 1%

---

### Q17: 如何提高计算精度？

**A**: 

1. **增加网格数**:
   ```json
   {
     "nx": 1000  // 默认500
   }
   ```

2. **减小时间步长**:
   ```json
   {
     "dt": 0.1  // 默认1.0
   }
   ```

3. **调整收敛容差**:
   ```json
   {
     "convergence_tol": 0.01  // 默认0.1
   }
   ```

**注意**: 精度提高会增加计算时间。

---

### Q18: 收敛问题怎么办？

**A**: 

**症状**: "求解器未收敛"错误

**解决方法**:

1. **检查参数合理性**:
   - 流量是否过大/过小？
   - 坡度是否合理？
   - 糙率是否合理？

2. **调整求解器参数**:
   ```json
   {
     "max_iter": 200,  // 增加迭代次数
     "convergence_tol": 1.0,  // 放宽容差
     "relaxation": 0.5  // 添加松弛因子
   }
   ```

3. **改进初始条件**:
   - 使用均匀流作为初始值
   - 逐步增加流量

---

### Q19: 数据格式是什么？

**A**: 

**输入格式**: JSON
```json
{
  "length": 10000,
  "width": 10,
  "slope": 0.001,
  "roughness": 0.025,
  "flow_rate": 50
}
```

**输出格式**:
- **JSON**: 轻量，易读
- **CSV**: 表格数据，Excel兼容
- **HDF5**: 大数据，高效压缩

**验证**: 自动JSON Schema验证。

---

### Q20: 可以批量运行吗？

**A**: 

可以！使用Python SDK:

```python
from hydro_sdk import HydroClient

client = HydroClient("http://localhost:8000")

# 批量配置
configs = [
  {"flow_rate": 50, ...},
  {"flow_rate": 100, ...},
  {"flow_rate": 150, ...}
]

# 批量运行
results = client.batch_run(configs)
```

参考: `examples/batch_processing/`

---

## 开发相关

### Q21: 如何开发插件？

**A**: 

**步骤**:

1. **阅读文档**:
   ```bash
   docs/plugins/getting-started.md
   ```

2. **创建插件**:
   ```
   my-plugin/
   ├── plugin.json
   ├── src/index.ts
   └── README.md
   ```

3. **实现功能**:
   ```typescript
   class MyPlugin implements Plugin {
     async onActivate(api: PluginAPI) {
       // 你的代码
     }
   }
   ```

4. **测试**:
   ```bash
   cp -r my-plugin plugins/examples/
   npm run dev:electron
   ```

**完整示例**: `plugins/examples/`

---

### Q22: 插件有哪些API？

**A**: 

8个标准API:

```typescript
api.simulation      // 仿真控制
api.visualization   // 图表扩展
api.data            // 数据处理
api.ui              // 界面扩展
api.utils           // 工具函数
api.storage         // 数据存储
api.events          // 事件系统
api.commands        // 命令系统
```

**详细文档**: `docs/plugins/api-reference.md`

---

### Q23: 如何贡献代码？

**A**: 

1. **Fork仓库**
2. **创建分支**: `git checkout -b feature/my-feature`
3. **开发和测试**
4. **提交**: `git commit -m "feat: add my feature"`
5. **推送**: `git push origin feature/my-feature`
6. **创建PR**

**详细指南**: `CONTRIBUTING.md`

---

### Q24: 如何报告Bug？

**A**: 

1. 访问 [GitHub Issues](https://github.com/hydroclaude/hydroclaude/issues)
2. 点击"New Issue"
3. 选择"Bug Report"模板
4. 填写详细信息:
   - 环境（OS, 版本）
   - 复现步骤
   - 期望结果
   - 实际结果
   - 截图（如有）

---

### Q25: 后端API在哪里？

**A**: 

**启动后端**:
```bash
cd backend
pip install -r requirements.txt
python run.py
```

**访问API文档**:
```
http://localhost:8000/docs
```

**Python SDK**:
```python
from hydro_sdk import HydroClient
client = HydroClient("http://localhost:8000")
```

---

## 性能优化

### Q26: 如何加快计算速度？

**A**: 

1. **减少网格数**:
   ```json
   {"nx": 200}  // 默认500
   ```

2. **使用静水压力求解器**:
   ```json
   {"solver": "hydrostatic"}
   ```

3. **增大时间步长**:
   ```json
   {"dt": 1.0}  // 根据CFL条件
   ```

4. **启用并行计算**（未来）:
   ```json
   {"parallel": true}
   ```

---

### Q27: 内存占用太高怎么办？

**A**: 

**正常内存占用**:
- 桌面应用: ~150MB
- Web应用: ~100MB

**如果过高**:

1. **减少网格数**
2. **关闭实时预览**
3. **清理缓存数据**
4. **重启应用**

**内存监控**:
- Windows: 任务管理器
- macOS: 活动监视器
- Linux: htop

---

### Q28: 大规模仿真建议？

**A**: 

**网格数 > 10000**:
- 使用HDF5格式
- 启用数据压缩
- 分段处理结果

**时间步数 > 10000**:
- 减少保存频率
- 使用后处理分析
- 考虑云计算（v3.0）

---

## 故障排除

### Q29: 无法启动怎么办？

**A**: 

**Windows**:
1. 检查防病毒软件
2. 以管理员身份运行
3. 重新安装

**macOS**:
1. 系统偏好设置 → 安全性
2. 允许"来自身份不明开发者"的应用
3. 或: `xattr -cr /Applications/HydroClaude.app`

**Linux**:
1. 检查执行权限: `chmod +x HydroClaude.AppImage`
2. 安装依赖: `sudo apt install libfuse2`

---

### Q30: 计算结果不合理？

**A**: 

**检查清单**:

1. **参数合理性**:
   - 流量: 1-1000 m³/s
   - 坡度: 0.0001-0.01
   - 糙率: 0.010-0.035
   - 宽度: 1-100 m

2. **边界条件**:
   - 上游: 流量或水深
   - 下游: 水深或自由出流

3. **数值稳定性**:
   - CFL条件
   - 网格质量

4. **验证**:
   - 查看流量验证图
   - 检查Froude数

**仍有问题**: 在GitHub提Issue。

---

### Q31: 更新失败？

**A**: 

**症状**: "更新下载失败"

**解决**:

1. **检查网络连接**
2. **手动下载**:
   - 访问 GitHub Releases
   - 下载最新版
   - 手动安装
3. **关闭防火墙/代理**

**跳过自动更新**:
- 设置 → 取消"自动检查更新"

---

### Q32: 数据丢失？

**A**: 

**自动备份**:
- 每次保存自动创建备份
- 位置: `Documents/HydroClaude/backups/`

**恢复数据**:
1. 文件 → 打开项目
2. 浏览到备份文件夹
3. 选择最近的备份

**建议**:
- 定期导出重要项目
- 使用版本控制（Git）

---

### Q33: 插件不工作？

**A**: 

**检查**:

1. **插件清单**:
   - `plugin.json`格式正确
   - 所有必需字段都有

2. **权限**:
   - 检查`permissions`数组
   - 确保有必要权限

3. **代码错误**:
   - 打开开发者工具 (Ctrl+Shift+I)
   - 查看控制台错误

4. **版本兼容**:
   - 检查`minVersion`和`maxVersion`

---

### Q34: Web界面空白？

**A**: 

**可能原因**:

1. **浏览器不兼容**:
   - 推荐: Chrome 90+, Firefox 88+
   - 升级浏览器

2. **JavaScript被禁用**:
   - 检查浏览器设置
   - 启用JavaScript

3. **缓存问题**:
   - 清除浏览器缓存
   - 硬刷新 (Ctrl+Shift+R)

4. **端口冲突**:
   - 默认端口5173
   - 更改: `npm run dev -- --port 3000`

---

### Q35: 无法连接后端API？

**A**: 

**检查**:

1. **后端是否运行**:
   ```bash
   cd backend
   python run.py
   ```

2. **端口是否正确**:
   - 默认: 8000
   - 访问: http://localhost:8000/health

3. **防火墙**:
   - 允许端口8000

4. **CORS设置**:
   - 检查`backend/.env`
   - `CORS_ORIGINS`包含前端地址

---

## 📞 获取更多帮助

### 文档资源

- [用户手册](./README.md)
- [插件开发指南](./docs/plugins/getting-started.md)
- [API参考](./docs/plugins/api-reference.md)
- [贡献指南](./CONTRIBUTING.md)

---

### 社区支持

- **GitHub Issues**: https://github.com/hydroclaude/hydroclaude/issues
- **Discussions**: https://github.com/hydroclaude/hydroclaude/discussions
- **Email**: dev@hydroclaude.com
- **Twitter**: @hydroclaude

---

### 快速链接

- [下载安装](https://github.com/hydroclaude/hydroclaude/releases)
- [源代码](https://github.com/hydroclaude/hydroclaude)
- [报告Bug](https://github.com/hydroclaude/hydroclaude/issues/new?template=bug_report.md)
- [请求功能](https://github.com/hydroclaude/hydroclaude/issues/new?template=feature_request.md)

---

## 💡 没有找到答案？

如果你的问题没有在这里找到答案：

1. **搜索已有Issue**: 可能有人已经问过
2. **创建新Issue**: 详细描述你的问题
3. **加入讨论区**: 与社区交流
4. **发邮件**: dev@hydroclaude.com

我们会尽快回复！

---

<p align="center">
  <b>💬 还有问题？欢迎提问！</b>
</p>

<p align="center">
  <i>HydroClaude - 让水力学仿真更简单</i>
</p>

---

**© 2025 HydroClaude Development Team**  
**Last Updated: 2025-11-15**
