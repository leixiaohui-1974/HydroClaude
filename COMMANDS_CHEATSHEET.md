# HydroClaude Commands Cheat Sheet
# 常用命令速查表

**Quick Reference for Common Tasks**  
**常用任务快速参考**

---

## 🚀 Starting the System / 启动系统

### Backend Server / 后端服务器

```bash
# Method 1: Basic start
python -m uvicorn web.backend.api_gateway.main:app --reload

# Method 2: Custom host and port
python -m uvicorn web.backend.api_gateway.main:app --reload --host 0.0.0.0 --port 8000

# Method 3: Background (Windows)
Start-Process python -ArgumentList "-m","uvicorn","web.backend.api_gateway.main:app","--reload" -WindowStyle Hidden
```

**Verify Backend**:
```bash
curl http://localhost:8000/health
# Or visit: http://localhost:8000/docs
```

### Frontend Server / 前端服务器

```bash
# Navigate to frontend directory
cd web/frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

**Access Frontend**: http://localhost:3000

---

## 🧪 Testing / 测试

### Quick Tests / 快速测试

```bash
# Test 5 random cases (快速验证)
python quick_test_sample.py

# Test specific directory
python quick_test_sample.py --directory examples
```

### Full Test Suite / 完整测试套件

```bash
# Run all 541 test cases
python batch_test_all_cases.py

# Run in background with output redirection
python batch_test_all_cases.py > test_results/batch_test_output.txt 2>&1 &

# Windows background
Start-Process python -ArgumentList "batch_test_all_cases.py" -RedirectStandardOutput "test_results\batch_test_output.txt"
```

### Monitor Testing / 监控测试

```bash
# Real-time progress monitor
python monitor_test_progress.py

# Auto-wait for completion and analyze
python wait_and_analyze.py

# Check test log (Linux/Mac)
tail -f test_results/batch_test_output.txt

# Check test log (Windows)
Get-Content test_results\batch_test_output.txt -Tail 50 -Wait
```

---

## 📊 Analysis / 分析

### Test Results Analysis / 测试结果分析

```bash
# Analyze test results
python analyze_test_results.py

# View generated report
# File: test_results/batch_test_analysis.md
```

### Automated Post-Test Workflow / 自动化测试后处理

```bash
# Run complete post-test workflow
python post_test_workflow.py

# This will:
# 1. Check test completion
# 2. Analyze results
# 3. Auto-fix issues
# 4. Generate summary
# 5. Verify fixes
```

---

## 🔧 Fixing Issues / 修复问题

### Auto-Fix Import Issues / 自动修复导入问题

```bash
# Dry run (see what would be fixed)
python fix_test_import_issues.py --directory tests

# Apply fixes to tests directory
python fix_test_import_issues.py --apply --directory tests

# Fix all directories
python fix_test_import_issues.py --apply --directory .

# Fix specific directory
python fix_test_import_issues.py --apply --directory examples
```

---

## 🌐 API Usage / API使用

### Health Check / 健康检查

```bash
curl http://localhost:8000/health
```

### Get Test Cases / 获取测试案例

```bash
# Get all test cases
curl http://localhost:8000/api/v1/test-cases/catalog

# Filter by category
curl "http://localhost:8000/api/v1/test-cases/filter?category=Dam%20Break"

# Search
curl "http://localhost:8000/api/v1/test-cases/search?q=gate"
```

### Run Simulation / 运行模拟

```bash
# Create simulation
curl -X POST http://localhost:8000/api/v1/simulation/create \
  -H "Content-Type: application/json" \
  -d '{
    "length": 10000,
    "width": 10,
    "discharge": 50,
    "simulation_time": 1000
  }'

# Check status
curl http://localhost:8000/api/v1/simulation/{id}/status

# Get results
curl http://localhost:8000/api/v1/simulation/{id}/results
```

### Run Test Case / 运行测试案例

```bash
# Run a test case
curl -X POST http://localhost:8000/api/v1/test-runner/run \
  -H "Content-Type: application/json" \
  -d '{"case_id": "examples-example_01_canal_flow-01_basic_v2"}'

# Check test status
curl http://localhost:8000/api/v1/test-runner/status/{task_id}

# Get test report
curl http://localhost:8000/api/v1/test-runner/results/{task_id}/report
```

---

## 📁 File Operations / 文件操作

### View Logs / 查看日志

```bash
# View last 50 lines (Linux/Mac)
tail -n 50 test_results/batch_test_output.txt

# View last 50 lines (Windows)
Get-Content test_results\batch_test_output.txt -Tail 50

# Search for errors
grep "ERROR\|FAIL" test_results/batch_test_output.txt

# Count passed tests
grep -c "PASS" test_results/batch_test_output.txt
```

### Clean Up / 清理

```bash
# Remove test results
rm -rf test_results/*

# Windows
Remove-Item test_results\* -Recurse -Force

# Remove backup files
rm test_fixes_backup/*.bak

# Clean Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
```

---

## 🐛 Debugging / 调试

### Check Process / 检查进程

```bash
# Check if backend is running (Linux/Mac)
ps aux | grep uvicorn

# Check if backend is running (Windows)
Get-Process | Where-Object {$_.ProcessName -like "*python*"}

# Check port usage
netstat -ano | findstr :8000
```

### View API Documentation / 查看API文档

```bash
# Open in browser
# Windows
start http://localhost:8000/docs

# Mac
open http://localhost:8000/docs

# Linux
xdg-open http://localhost:8000/docs
```

### Test Backend Connection / 测试后端连接

```bash
# Python
python -c "import requests; print(requests.get('http://localhost:8000/health').json())"

# curl
curl -v http://localhost:8000/health
```

---

## 📦 Package Management / 包管理

### Python Dependencies / Python依赖

```bash
# Install all dependencies
pip install -r requirements.txt

# Install specific package
pip install fastapi uvicorn numpy

# Check installed packages
pip list

# Update pip
python -m pip install --upgrade pip
```

### Frontend Dependencies / 前端依赖

```bash
cd web/frontend

# Install dependencies
npm install

# Update dependencies
npm update

# Check for outdated packages
npm outdated

# Install specific package
npm install ant-design@latest
```

---

## 🔍 Search & Find / 搜索查找

### Find Files / 查找文件

```bash
# Find all test files
find . -name "*test*.py"

# Find files modified today
find . -type f -mtime 0

# Find large files (>10MB)
find . -type f -size +10M
```

### Search in Files / 文件内容搜索

```bash
# Search for pattern in all Python files
grep -r "HydrostaticCanalSolver" --include="*.py"

# Search with line numbers
grep -rn "import sys" tests/

# Case-insensitive search
grep -ri "error" test_results/
```

---

## 📈 Performance / 性能

### Monitor Resources / 监控资源

```bash
# Monitor CPU and memory (Linux/Mac)
top
htop

# Monitor specific process
top -p $(pgrep -f uvicorn)

# Windows Task Manager
taskmgr
```

### Check Disk Usage / 检查磁盘使用

```bash
# Check directory size
du -sh test_results/

# Check disk space
df -h

# Windows
Get-ChildItem test_results | Measure-Object -Property Length -Sum
```

---

## 🎯 Quick Fixes / 快速修复

### Common Issues / 常见问题

```bash
# Issue: Port 8000 already in use
# Solution: Kill the process
# Linux/Mac:
lsof -ti:8000 | xargs kill -9
# Windows:
netstat -ano | findstr :8000
# Then: taskkill /PID <PID> /F

# Issue: Module not found
# Solution: Add to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Issue: Permission denied
# Solution: Make script executable
chmod +x *.py

# Issue: Encoding errors
# Solution: Set UTF-8 encoding
export LANG=en_US.UTF-8
export PYTHONIOENCODING=utf-8
```

---

## 📚 Documentation / 文档

### View Documentation / 查看文档

```bash
# Quick start guide
cat QUICK_START_COMPLETE.md

# Testing guide
cat TESTING_GUIDE.md

# API reference
cat LIBRARY_REFERENCE.md

# View in browser (Mac)
open QUICK_START_COMPLETE.md

# View in browser (Windows)
start QUICK_START_COMPLETE.md
```

---

## 🚀 Shortcuts / 快捷方式

### One-Line Commands / 单行命令

```bash
# Quick backend start
python -m uvicorn web.backend.api_gateway.main:app --reload &

# Quick frontend start
(cd web/frontend && npm run dev) &

# Quick test
python quick_test_sample.py

# Quick analysis
python analyze_test_results.py && cat test_results/batch_test_analysis.md

# Full workflow
python batch_test_all_cases.py && python analyze_test_results.py && python fix_test_import_issues.py --apply
```

### Aliases / 别名

```bash
# Add to ~/.bashrc or ~/.zshrc

alias hc-backend="python -m uvicorn web.backend.api_gateway.main:app --reload"
alias hc-frontend="cd web/frontend && npm run dev"
alias hc-test="python quick_test_sample.py"
alias hc-test-all="python batch_test_all_cases.py"
alias hc-analyze="python analyze_test_results.py"
alias hc-fix="python fix_test_import_issues.py --apply"
alias hc-monitor="python monitor_test_progress.py"
```

---

## 💡 Tips & Tricks / 技巧

### Productivity Tips / 效率提示

```bash
# Run multiple commands in sequence
python batch_test_all_cases.py && python analyze_test_results.py

# Run in background and redirect output
nohup python batch_test_all_cases.py > output.log 2>&1 &

# Set up watch for file changes
watch -n 2 'tail -10 test_results/batch_test_output.txt'

# Create workspace
mkdir -p workspace/{tests,results,logs}

# Backup before changes
cp -r test_results test_results_backup_$(date +%Y%m%d)
```

---

## ⚡ Power User Commands / 高级命令

### Advanced Testing / 高级测试

```bash
# Test with custom timeout
timeout 3600 python batch_test_all_cases.py

# Parallel testing (if supported)
python batch_test_all_cases.py --parallel 4

# Test specific category
python batch_test_all_cases.py --category "Dam Break"

# Generate HTML report
python analyze_test_results.py --format html
```

### Batch Operations / 批量操作

```bash
# Run all tests in sequence
for dir in tests examples validation_cases; do
    python fix_test_import_issues.py --apply --directory $dir
done

# Backup all results
tar -czf test_results_$(date +%Y%m%d_%H%M%S).tar.gz test_results/

# Clean all caches
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete
```

---

## 📞 Help & Support / 帮助与支持

### Get Help / 获取帮助

```bash
# Script help
python batch_test_all_cases.py --help
python analyze_test_results.py --help
python fix_test_import_issues.py --help

# Python help
python -c "import sys; help(sys)"

# Check versions
python --version
node --version
npm --version
```

---

**Last Updated**: 2025-11-13  
**Version**: 1.0

**🎯 Bookmark this page for quick reference!**



