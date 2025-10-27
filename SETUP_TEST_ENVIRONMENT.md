# 🔧 测试环境设置指南

## 📋 环境要求

### Python版本
- Python 3.7+

### 必需依赖

```bash
# 核心依赖
pip3 install numpy>=1.19.0
pip3 install scipy>=1.5.0
pip3 install matplotlib>=3.3.0
pip3 install pyyaml>=5.3.0

# 可选依赖（用于高级功能）
pip3 install pandas>=1.1.0  # 数据分析
pip3 install seaborn>=0.11.0  # 高级可视化
```

### 一键安装

```bash
cd /workspace
pip3 install -r requirements.txt
```

---

## 🚀 快速设置

### 方法1：使用pip

```bash
# 1. 安装所有依赖
pip3 install numpy scipy matplotlib pyyaml pandas

# 2. 验证安装
python3 -c "import numpy, scipy, matplotlib; print('✅ 所有依赖已安装')"

# 3. 运行测试
python3 run_comprehensive_tests.py --week 1
```

### 方法2：使用conda（推荐）

```bash
# 1. 创建虚拟环境
conda create -n hydroclaude python=3.9

# 2. 激活环境
conda activate hydroclaude

# 3. 安装依赖
conda install numpy scipy matplotlib pyyaml pandas

# 4. 运行测试
python run_comprehensive_tests.py --week 1
```

### 方法3：使用Docker

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /workspace

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "run_comprehensive_tests.py", "--all"]
```

```bash
# 构建和运行
docker build -t hydroclaude-test .
docker run hydroclaude-test
```

---

## ✅ 验证环境

运行验证脚本：

```bash
python3 check_environment.py
```

预期输出：

```
================================
环境检查
================================
✓ Python 3.9.x
✓ numpy 1.21.x
✓ scipy 1.7.x
✓ matplotlib 3.4.x
✓ pyyaml 5.4.x

================================
✅ 所有依赖已就绪
================================
```

---

## 🔍 故障排查

### 问题1：pip安装失败

```bash
# 升级pip
python3 -m pip install --upgrade pip

# 使用清华源
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple numpy scipy matplotlib
```

### 问题2：权限错误

```bash
# 使用用户安装
pip3 install --user numpy scipy matplotlib
```

### 问题3：版本冲突

```bash
# 使用虚拟环境
python3 -m venv venv
source venv/bin/activate
pip install numpy scipy matplotlib
```

---

## 📊 运行测试

### Week 1：解析解验证

```bash
# 完整测试（51个工况，5-10分钟）
python3 run_comprehensive_tests.py --week 1

# 快速测试（10个工况，1-2分钟）
python3 tests/test_analytical_validation_quick.py
```

### Week 2-4

```bash
# Week 2：国际基准算例
python3 run_comprehensive_tests.py --week 2

# Week 3：极端条件
python3 run_comprehensive_tests.py --week 3

# Week 4：长时间稳定性
python3 run_comprehensive_tests.py --week 4

# 或运行全部（1-2小时）
python3 run_comprehensive_tests.py --all
```

---

## 📈 性能要求

### 最低配置
- CPU: 2核
- 内存: 4GB
- 磁盘: 1GB

### 推荐配置
- CPU: 4核+
- 内存: 8GB+
- 磁盘: 2GB+

### 运行时间估算
- Week 1: 5-10分钟
- Week 2: 10-20分钟
- Week 3: 20-30分钟
- Week 4: 30-60分钟
- 全部: 1-2小时

---

## 🎯 下一步

环境设置完成后：

1. **运行Week 1测试**
   ```bash
   python3 run_comprehensive_tests.py --week 1
   ```

2. **查看报告**
   ```bash
   cat week1_analytical_validation_report.md
   ```

3. **分析结果**
   - 如果通过率>95%：继续Week 2
   - 如果通过率80-95%：分析改进
   - 如果通过率<80%：修复核心问题

---

## 📞 获取帮助

如果遇到问题：

1. 查看详细日志
   ```bash
   python3 run_comprehensive_tests.py --week 1 --verbose
   ```

2. 检查环境
   ```bash
   python3 check_environment.py
   ```

3. 查看测试框架文档
   ```bash
   cat COMPREHENSIVE_TEST_PLAN.md
   ```

---

**准备好后，开始测试！** 🚀
