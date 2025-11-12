# HydroClaude Web - 5分钟快速开始

> **最快的方式开始使用和测试系统**

## 🚀 最快开始（3个命令）

```bash
# 1. 启动服务
cd /workspace/web && ./start_servers.sh && sleep 15

# 2. 运行测试
python3 ultimate_test.py

# 3. 查看结果
cat ultimate_test_report.json | python3 -m json.tool
```

## 📊 查看测试报告

```bash
# 完整报告（推荐）
cat FINAL_COMPREHENSIVE_REPORT.md | less

# 快速查看结果
grep -A 5 "summary" ultimate_test_report.json
```

## 📸 查看截图

```bash
# 列出所有截图
ls -lh ultimate_screenshots/

# 在文件管理器中打开（如果有GUI）
# open ultimate_screenshots/
# 或 xdg-open ultimate_screenshots/
```

## 🧹 清理测试文件

```bash
./cleanup_tests.sh
```

## ❓ 遇到问题？

查看详细指南：
```bash
cat TEST_EXECUTION_GUIDE.md
```

或查看故障排查：
```bash
cat TEST_EXECUTION_GUIDE.md | grep -A 50 "故障排查"
```

---

**就这么简单！** 🎉
