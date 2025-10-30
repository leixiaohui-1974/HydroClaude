# HydroClaude Jupyter Notebook 教程
# HydroClaude Jupyter Notebook Tutorials

欢迎使用HydroClaude交互式教程！这些Jupyter Notebook提供了循序渐进的学习路径，帮助您掌握水力学分析的各个方面。

Welcome to HydroClaude interactive tutorials! These Jupyter Notebooks provide a step-by-step learning path to help you master various aspects of hydraulic analysis.

---

## 📚 教程列表 / Tutorial List

### 1. 快速入门 / Quick Start
**文件**: `01_quick_start.ipynb`
**难度**: 初级 / Beginner
**时长**: 15分钟

**学习内容**:
- 创建简单的管网拓扑
- 配置节点和管道
- 使用Hardy Cross求解器
- 分析计算结果
- 可视化结果

**适合对象**: 初学者，第一次使用HydroClaude

---

### 2. 环状管网分析 / Looped Network Analysis
**文件**: `02_looped_network.ipynb`
**难度**: 中级 / Intermediate
**时长**: 25分钟

**学习内容**:
- 创建环状管网拓扑
- 理解Hardy Cross方法原理
- 分析环路流量分配
- 多工况对比分析
- 优化管网设计

**适合对象**: 已掌握基础操作，想深入了解环状管网分析

---

### 3. 水锤分析 / Water Hammer Analysis
**文件**: `03_water_hammer.ipynb`
**难度**: 高级 / Advanced
**时长**: 35分钟

**学习内容**:
- 理解水锤现象的物理机制
- 使用Joukowsky公式估算压力升高
- 使用MOC方法进行瞬态模拟
- 分析阀门关闭引起的水锤
- 设计水锤防护措施

**适合对象**: 需要进行瞬态分析的工程师

---

## 🚀 使用方法 / How to Use

### 方法1: Jupyter Notebook
```bash
# 1. 确保已安装Jupyter
pip install jupyter

# 2. 启动Jupyter Notebook
jupyter notebook

# 3. 在浏览器中打开相应的.ipynb文件
```

### 方法2: JupyterLab (推荐)
```bash
# 1. 安装JupyterLab
pip install jupyterlab

# 2. 启动JupyterLab
jupyter lab

# 3. 在左侧文件浏览器中打开tutorials目录
```

### 方法3: VS Code
```bash
# 1. 安装VS Code的Jupyter扩展

# 2. 在VS Code中打开.ipynb文件

# 3. 点击"Run All"运行所有单元格
```

---

## 📦 依赖要求 / Requirements

### 必需 / Required
```bash
numpy>=1.20.0
matplotlib>=3.3.0
```

### 推荐 / Recommended
```bash
jupyter>=1.0.0
jupyterlab>=3.0.0
ipywidgets>=7.6.0  # 交互式控件
```

安装所有依赖：
```bash
pip install -r ../requirements.txt
```

---

## 📖 学习路径 / Learning Path

### 初学者路径
1. ✅ 教程1：快速入门
2. ✅ 案例1：城市供水管网分析 (`examples/case1_urban_water_supply.py`)
3. ✅ 教程2：环状管网分析
4. ✅ 案例3：工业供水系统 (`examples/case3_industrial_cooling_system.py`)

### 进阶路径
1. ✅ 教程3：水锤分析
2. ✅ 案例2：泵站水锤分析 (`examples/case2_pump_water_hammer.py`)
3. ✅ 案例4-8：各类工程应用

### 专业路径
1. ✅ 深入研究源代码
2. ✅ 开发自定义求解器
3. ✅ 贡献代码到开源项目

---

## 💡 学习建议 / Learning Tips

### 1. 循序渐进
- 按顺序完成教程
- 确保理解每个概念后再继续
- 不要跳过练习部分

### 2. 动手实践
- 修改参数，观察结果变化
- 尝试解决实际工程问题
- 创建自己的案例

### 3. 深入理解
- 阅读理论背景
- 理解数学公式的物理意义
- 查阅相关文献

### 4. 交流讨论
- 在GitHub Issues提问
- 分享你的应用案例
- 参与社区讨论

---

## 🎯 后续教程计划 / Future Tutorials

即将推出 / Coming Soon:
- [ ] 教程4：管网优化与经济分析
- [ ] 教程5：水质模拟
- [ ] 教程6：GIS数据集成
- [ ] 教程7：实时监测与数字孪生

---

## 📚 参考资料 / References

### 书籍
1. "水力学" - 吴持恭
2. "给水排水管网系统" - 严煦世
3. "Hydraulics in Civil and Environmental Engineering" - Andrew Chadwick

### 在线资源
- HydroClaude官方文档: `docs/`
- API参考: `docs/api/`
- 案例库: `examples/`

### 相关软件
- EPANET: 管网水力和水质模拟
- HAMMER: 水锤分析
- WaterCAD/WaterGEMS: 商业管网软件

---

## 🤝 贡献 / Contributing

欢迎贡献新的教程！

如果您想贡献教程，请：
1. Fork本项目
2. 创建新的Jupyter Notebook
3. 遵循现有教程的格式和风格
4. 提交Pull Request

**教程要求**:
- 清晰的学习目标
- 循序渐进的内容组织
- 丰富的代码示例
- 详细的注释和解释
- 可视化结果
- 中英双语

---

## 📄 许可证 / License

这些教程采用与HydroClaude相同的许可证。

---

## 📮 联系方式 / Contact

- GitHub Issues: https://github.com/yourusername/HydroClaude/issues
- Email: your.email@example.com

---

**祝学习愉快！/ Happy Learning!** 🎉

*最后更新 / Last Updated: 2025-10-30*
