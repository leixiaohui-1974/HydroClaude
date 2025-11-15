# ⭐ START HERE - HydroClaude 快速参考

**最后更新**: 2025-11-15  
**当前版本**: v1.0.0  
**状态**: ✅ Phase 1-2 完成

---

## 🚀 30秒了解项目

**HydroClaude** = 开源版HEC-RAS + 现代化Web界面 + Python生态

- ✅ 340,000行代码，35个求解器
- ✅ 统一程序入口 + 配置驱动
- ✅ 标准化I/O + Web查看器
- ✅ 对标商业软件（HEC-RAS/MIKE）

---

## 📚 核心文档（必读 3个）

### 1. 快速开始 ⭐⭐⭐
**文件**: `🌟_QUICK_START.md`  
**用途**: 5分钟上手  
**内容**: 安装、运行、查看结果

### 2. 架构设计 ⭐⭐⭐
**文件**: `COMMERCIAL_ARCHITECTURE_V2.md`  
**用途**: 深入理解系统  
**内容**: 通用数据模型、Web标准化、设计理念

### 3. 产品战略 ⭐⭐⭐
**文件**: `PRODUCT_STRATEGY_COMMERCIAL.md`  
**用途**: 了解项目定位  
**内容**: 现状分析、对标商业软件、开发路线图

---

## 🎯 快速上手（3步）

```bash
# 1. 安装依赖
pip install numpy pandas matplotlib jsonschema

# 2. 运行示例
python3 hydro_engine.py examples_config/01_steady_canal.json

# 3. 查看结果
open results/01_steady_canal/web/index.html
```

**就这么简单！**

---

## 📂 项目结构速览

```
HydroClaude/
├── hydro_engine.py              ⭐ 唯一程序入口
├── core/                         新架构核心
│   ├── config_parser.py          配置解析
│   ├── simulation_engine.py      仿真引擎
│   └── output_manager.py         输出管理
├── templates/                    Web模板
│   ├── hydro_viewer.js           交互逻辑
│   ├── index_template.html       HTML结构
│   └── styles.css                样式
├── examples_config/              配置示例
│   ├── 01_steady_canal.json
│   ├── 02_gate_flow.json
│   └── 03_unsteady_flow.json
├── solvers/                      求解器（35个类）
├── utils/                        工具库（29个）
└── results/                      输出（自动生成）
```

---

## 🎯 核心概念

### 1. 单一入口
```bash
python3 hydro_engine.py config.json
```
所有场景都用这一个命令！

### 2. 配置驱动
修改JSON，不改代码：
```json
{
  "canal": {"length": 1000, "width": 10},
  "solver": {"method": "hydrostatic"},
  "output": {"directory": "results/my_case"}
}
```

### 3. 标准化输出
所有场景统一格式：
```
results/[case]/
├── results.json        # 标准数据
├── data/               # CSV/HDF5
├── plots/              # 图表
├── reports/            # 报告
└── web/index.html      # Web查看器
```

### 4. Web查看器
自动适配所有场景：
- 稳态 → 显示空间剖面
- 非恒定流 → 增加时间序列
- 有结构 → 增加结构分析

---

## 💡 常见问题

### Q1: 如何运行仿真？
```bash
python3 hydro_engine.py config.json
```

### Q2: 如何修改参数？
编辑 `config.json`，无需改代码

### Q3: 结果在哪里？
`results/[case_name]/web/index.html`

### Q4: 如何添加闸门？
```json
{
  "structures": [
    {"type": "sluice_gate", "position": 5000, "parameters": {...}}
  ]
}
```

### Q5: 如何生成配置模板？
```bash
python3 hydro_engine.py --template steady_canal
```

---

## 📊 项目现状

### 规模
- **代码**: 340,000行（企业级）
- **求解器**: 35个类
- **示例**: 174个
- **新架构**: 3,400行

### 能力
- ✅ 稳态/非恒定流
- ✅ 水工结构（17种）
- ✅ 网络求解
- ✅ 冰情模拟（独有）
- ✅ 数字孪生（前沿）

### 对比商业软件
| 特性 | HEC-RAS | HydroClaude |
|------|---------|-------------|
| Web界面 | ❌ | ✅ |
| Python API | ❌ | ✅ |
| 开源 | ⚠️ | ✅ |
| 冰情模拟 | ❌ | ✅ |

---

## 🎓 学习路径

### 新手（10分钟）
1. 读 `🌟_QUICK_START.md`
2. 运行示例
3. 查看Web结果

### 进阶（1小时）
1. 读 `COMMERCIAL_ARCHITECTURE_V2.md`
2. 修改配置参数
3. 运行自己的场景

### 开发者（1天）
1. 读 `PRODUCT_STRATEGY_COMMERCIAL.md`
2. 查看源码 `core/`
3. 阅读 `LIBRARY_REFERENCE.md`

---

## 🏆 核心优势

### vs HEC-RAS
- ✅ 现代化Web界面
- ✅ 完整CLI支持
- ✅ Python原生API
- ✅ 100%开源

### vs MIKE 11
- ✅ 免费
- ✅ 配置更简单（JSON vs M11）
- ✅ Web展示更好
- ✅ 可编程性更强

### 独有特性
- ✅ 冰情模拟
- ✅ 数字孪生
- ✅ 先进控制（MPC）

---

## 📅 开发路线

```
✅ Phase 1: 统一架构（完成）
✅ Phase 2: Web查看器（完成）
⏰ Phase 3: 高级功能（1个月）
⏰ Phase 4: API/SDK（3个月）
⏰ Phase 5: GUI（6个月）
⏰ Phase 6: 2D/AI（长期）
```

---

## 🛠️ 命令速查

```bash
# 运行仿真
python3 hydro_engine.py config.json

# 验证配置
python3 hydro_engine.py config.json --validate

# 查看摘要
python3 hydro_engine.py config.json --summary

# 详细输出
python3 hydro_engine.py config.json --verbose

# 生成模板
python3 hydro_engine.py --template steady_canal

# 查看版本
python3 hydro_engine.py --version

# 查看帮助
python3 hydro_engine.py -h
```

---

## 📞 获取帮助

### 文档
- **快速开始**: `🌟_QUICK_START.md`
- **完整报告**: `🎊_商业级产品开发_PHASE1-2_完成报告.md`
- **示例说明**: `examples_config/README.md`

### 社区
- GitHub: [待创建]
- 文档: 本项目 `*.md` 文件
- 问题: [待设置]

---

## 🎉 立即开始

### 选项1: 最快（1分钟）
```bash
python3 hydro_engine.py examples_config/01_steady_canal.json
open results/01_steady_canal/web/index.html
```

### 选项2: 自定义（5分钟）
```bash
python3 hydro_engine.py --template steady_canal
# 编辑 config_template_steady_canal.json
python3 hydro_engine.py config_template_steady_canal.json
```

### 选项3: 深入学习（30分钟）
```bash
# 阅读文档
cat 🌟_QUICK_START.md
cat COMMERCIAL_ARCHITECTURE_V2.md

# 运行所有示例
for config in examples_config/*.json; do
    python3 hydro_engine.py "$config"
done
```

---

## ⚡ 核心理念

> **"一个程序入口 + 统一数据模型 + 标准化展示"**

**之前**:
- 174个独立脚本
- 修改代码调参数
- 输出格式混乱

**现在**:
- 1个统一命令
- JSON配置驱动
- 标准化结果 + Web查看器

**这就是商业级软件！** ✨

---

**欢迎使用HydroClaude！**

**From Scripts to Commercial Software** 🚀

---

**HydroClaude Development Team**  
**Version 1.0.0 | 2025-11-15**
