# 🔧 HydroClaude Web 维护和运维指南

> **版本**: v1.0  
> **最后更新**: 2025-11-12  
> **目标读者**: 运维工程师、系统管理员

---

## 🎯 维护概述

本指南涵盖 HydroClaude Web 系统的日常维护、监控、故障排查和优化。

---

## 📋 目录

1. [日常维护任务](#1️⃣-日常维护任务)
2. [健康检查](#2️⃣-健康检查)
3. [性能监控](#3️⃣-性能监控)
4. [日志管理](#4️⃣-日志管理)
5. [备份和恢复](#5️⃣-备份和恢复)
6. [故障排查](#6️⃣-故障排查)
7. [安全维护](#7️⃣-安全维护)
8. [容量规划](#8️⃣-容量规划)
9. [更新和升级](#9️⃣-更新和升级)
10. [应急响应](#🔟-应急响应)

---

## 1️⃣ 日常维护任务

### 每日任务（15分钟）

#### 1.1 服务状态检查

```bash
#!/bin/bash
# daily_check.sh

echo "=== HydroClaude 每日健康检查 ==="
echo "时间: $(date)"
echo ""

# 1. 检查服务状态
echo "1. 服务状态："
systemctl is-active hydroclaude-backend || echo "❌ 后端服务异常"
systemctl is-active nginx || echo "❌ Nginx异常"

# 2. 检查端口
echo ""
echo "2. 端口监听："
netstat -tlnp | grep -E ":8000|:80|:443" || echo "❌ 端口监听异常"

# 3. 检查磁盘空间
echo ""
echo "3. 磁盘空间："
df -h | grep -E "/$|/var"

# 4. 检查内存使用
echo ""
echo "4. 内存使用："
free -h

# 5. 健康检查API
echo ""
echo "5. API健康检查："
curl -s http://localhost:8000/api/health | python3 -m json.tool || echo "❌ API异常"

# 6. 检查错误日志
echo ""
echo "6. 最近错误（最近1小时）："
journalctl -u hydroclaude-backend --since "1 hour ago" | grep -i error | tail -5

echo ""
echo "=== 检查完成 ==="
```

**执行方式**：
```bash
chmod +x daily_check.sh
./daily_check.sh
```

**预期结果**：
- ✅ 所有服务运行正常
- ✅ 磁盘使用 < 80%
- ✅ 内存使用 < 80%
- ✅ API健康检查通过
- ✅ 无严重错误日志

#### 1.2 性能快速检查

```bash
# 检查API响应时间
time curl -s http://localhost:8000/api/engine/info > /dev/null

# 预期：< 100ms

# 检查系统负载
uptime

# 预期：load average < CPU核心数
```

### 每周任务（30分钟）

#### 2.1 完整性检查

```bash
#!/bin/bash
# weekly_check.sh

echo "=== HydroClaude 每周检查 ==="

# 1. 运行完整测试套件
echo "1. 运行测试套件..."
cd /var/www/hydroclaude/web
python3 ultimate_test.py > weekly_test_$(date +%Y%m%d).log 2>&1

# 2. 检查依赖更新
echo "2. 检查依赖更新..."
pip3 list --outdated
npm outdated

# 3. 安全扫描
echo "3. 安全扫描..."
pip3 check
npm audit

# 4. 清理旧日志
echo "4. 清理旧日志（>30天）..."
find /var/log -name "*.log" -mtime +30 -delete

# 5. 数据库维护
echo "5. 数据库维护..."
# psql $DATABASE_URL -c "VACUUM ANALYZE;"

echo "=== 检查完成 ==="
```

#### 2.2 备份验证

```bash
# 验证最新备份
ls -lh /backups/database/ | head -5

# 测试恢复（在测试环境）
# pg_restore -d test_db /backups/database/latest.dump
```

### 每月任务（1小时）

#### 3.1 性能审计

```bash
# 1. 分析慢查询日志（如果启用）
# 2. 检查数据库索引效率
# 3. 审查API响应时间趋势
# 4. 分析用户访问模式
# 5. 容量规划评估
```

#### 3.2 安全审计

```bash
# 1. 检查SSL证书到期时间
openssl x509 -in /etc/letsencrypt/live/yourdomain.com/cert.pem -noout -dates

# 2. 审查访问日志，查找异常
tail -1000 /var/log/nginx/access.log | awk '{print $1}' | sort | uniq -c | sort -rn | head -20

# 3. 检查失败的登录尝试
# 4. 更新安全策略
# 5. 依赖漏洞扫描
```

---

## 2️⃣ 健康检查

### 2.1 服务健康检查

**后端健康检查**：
```bash
curl -s http://localhost:8000/api/health | python3 -m json.tool
```

**预期响应**：
```json
{
  "status": "healthy",
  "timestamp": "2025-11-12T10:00:00Z",
  "version": "1.0.0",
  "database": "connected",
  "cache": "connected"
}
```

### 2.2 自动化健康检查

**创建监控脚本**：
```bash
#!/bin/bash
# health_monitor.sh

while true; do
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health)
    
    if [ "$response" != "200" ]; then
        echo "$(date): ❌ 健康检查失败，HTTP状态码: $response" | tee -a /var/log/health_monitor.log
        # 发送告警
        # send_alert "HydroClaude健康检查失败"
    else
        echo "$(date): ✅ 健康检查通过" >> /var/log/health_monitor.log
    fi
    
    sleep 60  # 每分钟检查一次
done
```

**设置为systemd服务**：
```ini
# /etc/systemd/system/hydroclaude-monitor.service
[Unit]
Description=HydroClaude Health Monitor
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/health_monitor.sh
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 3️⃣ 性能监控

### 3.1 关键指标

**应用层指标**：
- API响应时间（平均、P95、P99）
- 请求成功率
- 错误率
- 并发用户数

**系统层指标**：
- CPU使用率
- 内存使用率
- 磁盘I/O
- 网络带宽

**数据库指标**：
- 连接数
- 查询响应时间
- 慢查询数量
- 缓存命中率

### 3.2 性能监控命令

**实时监控**：
```bash
# CPU和内存
htop

# 磁盘I/O
iotop

# 网络
iftop

# 进程监控
ps aux | grep -E "uvicorn|nginx" | grep -v grep
```

**API性能测试**：
```bash
# 使用ab（Apache Bench）
ab -n 1000 -c 10 http://localhost:8000/api/health

# 使用wrk
wrk -t4 -c100 -d30s http://localhost:8000/api/health
```

### 3.3 性能基线

**正常运行基线**（来自测试结果）：
```
API平均响应时间:    0.9ms    ⚡⚡⚡⚡⚡
API P95响应时间:    1.5ms    ⚡⚡⚡⚡⚡
API P99响应时间:    1.7ms    ⚡⚡⚡⚡⚡
前端首次加载:       0.69s    ⚡⚡⚡⚡⚡
并发100成功率:      100%     ✅
CPU使用率:          < 50%    ✅
内存使用率:         < 70%    ✅
```

**告警阈值**：
```
API平均响应 > 10ms       ⚠️  警告
API平均响应 > 50ms       🚨 严重
前端加载 > 3秒          ⚠️  警告
前端加载 > 5秒          🚨 严重
错误率 > 1%             ⚠️  警告
错误率 > 5%             🚨 严重
CPU使用 > 80%           ⚠️  警告
内存使用 > 85%          ⚠️  警告
磁盘使用 > 85%          ⚠️  警告
```

---

## 4️⃣ 日志管理

### 4.1 日志位置

```
应用日志：
  • /var/log/hydroclaude/app.log
  • /var/log/hydroclaude/error.log

Systemd日志：
  • journalctl -u hydroclaude-backend

Web服务器日志：
  • /var/log/nginx/access.log
  • /var/log/nginx/error.log

系统日志：
  • /var/log/syslog
```

### 4.2 常用日志命令

```bash
# 查看实时日志
sudo journalctl -u hydroclaude-backend -f

# 查看最近1小时日志
sudo journalctl -u hydroclaude-backend --since "1 hour ago"

# 查看错误日志
sudo journalctl -u hydroclaude-backend -p err

# 搜索特定关键词
sudo journalctl -u hydroclaude-backend | grep -i "error"

# 导出日志
sudo journalctl -u hydroclaude-backend --since "2025-11-12" > logs_20251112.txt
```

### 4.3 日志轮转

**配置文件**：`/etc/logrotate.d/hydroclaude`

```
/var/log/hydroclaude/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload hydroclaude-backend > /dev/null 2>&1 || true
    endscript
}
```

### 4.4 日志分析

**常见问题检测**：
```bash
# 统计错误类型
grep -i error /var/log/hydroclaude/app.log | awk '{print $5}' | sort | uniq -c | sort -rn

# 统计最慢的API
grep "response_time" /var/log/hydroclaude/app.log | sort -t: -k5 -rn | head -10

# 统计访问IP
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -20
```

---

## 5️⃣ 备份和恢复

### 5.1 备份策略

**备份频率**：
- 数据库：每日全量备份，每小时增量备份
- 代码：每次部署前备份
- 配置文件：每次修改后备份

**保留策略**：
- 每日备份：保留30天
- 每周备份：保留12周
- 每月备份：保留12个月

### 5.2 数据库备份

**自动备份脚本**：
```bash
#!/bin/bash
# backup_database.sh

BACKUP_DIR="/backups/database"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="hydroclaude_${DATE}.sql"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 执行备份
pg_dump $DATABASE_URL > "$BACKUP_DIR/$FILENAME"

# 压缩
gzip "$BACKUP_DIR/$FILENAME"

# 删除30天前的备份
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

# 验证备份
if [ -f "$BACKUP_DIR/${FILENAME}.gz" ]; then
    echo "✅ 备份成功: ${FILENAME}.gz"
    # 可选：上传到远程存储
    # aws s3 cp "$BACKUP_DIR/${FILENAME}.gz" s3://your-bucket/backups/
else
    echo "❌ 备份失败"
    exit 1
fi
```

**设置定时任务**：
```bash
# 编辑crontab
crontab -e

# 添加每日凌晨2点备份
0 2 * * * /usr/local/bin/backup_database.sh >> /var/log/backup.log 2>&1
```

### 5.3 数据库恢复

**恢复步骤**：
```bash
# 1. 停止应用
sudo systemctl stop hydroclaude-backend

# 2. 创建数据库快照（以防万一）
pg_dump $DATABASE_URL > before_restore_$(date +%Y%m%d).sql

# 3. 解压备份
gunzip /backups/database/hydroclaude_20251112_020000.sql.gz

# 4. 恢复数据库
psql $DATABASE_URL < /backups/database/hydroclaude_20251112_020000.sql

# 5. 验证数据
psql $DATABASE_URL -c "SELECT COUNT(*) FROM simulations;"

# 6. 重启应用
sudo systemctl start hydroclaude-backend

# 7. 健康检查
curl http://localhost:8000/api/health
```

### 5.4 配置文件备份

```bash
# 备份配置文件
tar -czf config_backup_$(date +%Y%m%d).tar.gz \
    /etc/nginx/sites-available/hydroclaude \
    /etc/systemd/system/hydroclaude-*.service \
    /var/www/hydroclaude/.env
```

---

## 6️⃣ 故障排查

### 6.1 常见问题和解决方案

#### 问题1: 服务无法启动

**症状**：`systemctl status hydroclaude-backend` 显示 `failed`

**排查步骤**：
```bash
# 1. 查看详细错误
sudo journalctl -u hydroclaude-backend -n 50 --no-pager

# 2. 检查配置文件
sudo systemctl cat hydroclaude-backend

# 3. 手动启动测试
cd /var/www/hydroclaude/backend
/var/www/hydroclaude/venv/bin/uvicorn api_gateway.test_server:app --host 0.0.0.0 --port 8000

# 4. 检查端口占用
sudo netstat -tlnp | grep 8000
```

**常见原因**：
- ✓ 端口被占用 → `sudo kill $(lsof -t -i:8000)`
- ✓ 环境变量未设置 → 检查 `.env` 文件
- ✓ 依赖缺失 → `pip3 install -r requirements.txt`
- ✓ 权限问题 → `sudo chown -R www-data:www-data /var/www/hydroclaude`

#### 问题2: API响应慢

**症状**：API响应时间 > 100ms

**排查步骤**：
```bash
# 1. 检查系统负载
uptime
top

# 2. 检查数据库性能
# psql $DATABASE_URL -c "SELECT * FROM pg_stat_activity;"

# 3. 检查慢查询
# psql $DATABASE_URL -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# 4. 检查应用日志
sudo journalctl -u hydroclaude-backend | grep -i "slow"
```

**解决方案**：
- ✓ 添加数据库索引
- ✓ 启用缓存（Redis）
- ✓ 优化查询语句
- ✓ 增加worker数量

#### 问题3: 内存使用过高

**症状**：内存使用 > 85%

**排查步骤**：
```bash
# 1. 查看内存使用详情
free -h
top -o %MEM

# 2. 查看进程内存使用
ps aux --sort=-%mem | head -10

# 3. 检查是否有内存泄漏
# 重启服务后观察内存增长趋势
```

**解决方案**：
- ✓ 重启服务释放内存
- ✓ 增加物理内存
- ✓ 优化代码（修复内存泄漏）
- ✓ 调整worker数量

#### 问题4: 磁盘空间不足

**症状**：磁盘使用 > 90%

**排查步骤**：
```bash
# 1. 查看磁盘使用
df -h

# 2. 找出大文件
du -sh /var/* | sort -rh | head -10

# 3. 检查日志文件大小
du -sh /var/log/*
```

**解决方案**：
```bash
# 清理旧日志
sudo find /var/log -name "*.log" -mtime +30 -delete

# 清理旧备份
sudo find /backups -name "*.sql.gz" -mtime +30 -delete

# 清理临时文件
sudo rm -rf /tmp/*

# 清理Docker资源（如果使用）
# docker system prune -a
```

### 6.2 故障排查流程图

```
服务异常
    │
    ├─ 服务无法启动？
    │   └─ 检查配置文件、端口、权限
    │
    ├─ API不响应？
    │   └─ 检查网络、防火墙、Nginx配置
    │
    ├─ 响应慢？
    │   └─ 检查负载、数据库、慢查询
    │
    ├─ 错误频繁？
    │   └─ 检查日志、数据库连接、依赖
    │
    └─ 其他问题？
        └─ 查看详细日志，联系技术支持
```

---

## 7️⃣ 安全维护

### 7.1 定期安全任务

**每周**：
```bash
# 1. 更新系统软件包
sudo apt update
sudo apt upgrade

# 2. 检查安全漏洞
npm audit
pip3 check

# 3. 审查访问日志
sudo tail -1000 /var/log/nginx/access.log | grep -E "POST|DELETE|PUT"
```

**每月**：
```bash
# 1. 更新SSL证书（自动续期）
sudo certbot renew

# 2. 审查用户权限
# 3. 检查防火墙规则
sudo ufw status
```

### 7.2 安全加固

```bash
# 1. 限制SSH访问
# 编辑 /etc/ssh/sshd_config
# PermitRootLogin no
# PasswordAuthentication no

# 2. 配置防火墙
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 3. 安装fail2ban
sudo apt install fail2ban
```

---

## 8️⃣ 容量规划

### 8.1 增长趋势分析

**监控指标**：
- 日均请求数
- 用户数增长
- 数据库大小增长
- 存储空间使用

### 8.2 扩展建议

**何时扩展**：
- CPU使用持续 > 70%
- 内存使用持续 > 75%
- 磁盘使用 > 80%
- API响应时间 > 50ms

**扩展方案**：
1. **垂直扩展**：升级服务器配置
2. **水平扩展**：增加服务器数量，使用负载均衡
3. **数据库优化**：读写分离，主从复制
4. **缓存层**：引入Redis缓存

---

## 9️⃣ 更新和升级

### 9.1 应用更新流程

```bash
# 1. 备份当前版本
./backup_database.sh
tar -czf app_backup_$(date +%Y%m%d).tar.gz /var/www/hydroclaude

# 2. 拉取新代码
cd /var/www/hydroclaude
git pull origin main

# 3. 安装依赖
pip3 install -r requirements.txt
cd frontend && npm install && npm run build

# 4. 数据库迁移（如有）
# alembic upgrade head

# 5. 重启服务
sudo systemctl restart hydroclaude-backend
sudo systemctl reload nginx

# 6. 验证
curl http://localhost:8000/api/health
python3 ultimate_test.py
```

### 9.2 回滚流程

```bash
# 1. 停止服务
sudo systemctl stop hydroclaude-backend

# 2. 恢复代码
cd /var/www/hydroclaude
git checkout <previous-tag>

# 3. 恢复数据库（如需要）
# psql $DATABASE_URL < backup_before_upgrade.sql

# 4. 重启服务
sudo systemctl start hydroclaude-backend

# 5. 验证
curl http://localhost:8000/api/health
```

---

## 🔟 应急响应

### 10.1 紧急联系方式

```
技术负责人：_________ (手机：_________)
数据库管理员：_______ (手机：_________)
网络工程师：_________ (手机：_________)
云服务商支持：_______ (服务编号：___)
```

### 10.2 应急处理流程

#### P0级故障（系统完全不可用）

**响应时间**: 5分钟内

**处理步骤**：
1. 确认故障范围
2. 启用备用系统（如有）
3. 通知所有相关人员
4. 快速诊断和修复
5. 记录故障详情

#### P1级故障（核心功能受影响）

**响应时间**: 15分钟内

**处理步骤**：
1. 评估影响范围
2. 隔离问题
3. 实施修复
4. 验证功能恢复
5. 发布公告

#### P2级故障（部分功能受影响）

**响应时间**: 1小时内

**处理步骤**：
1. 记录问题
2. 排入修复队列
3. 计划修复时间
4. 实施并验证
5. 更新文档

### 10.3 快速恢复命令

```bash
# 快速重启所有服务
sudo systemctl restart hydroclaude-backend nginx

# 快速回滚到上一版本
cd /var/www/hydroclaude && git checkout HEAD~1 && sudo systemctl restart hydroclaude-backend

# 清理并重启
sudo systemctl stop hydroclaude-backend
ps aux | grep uvicorn | grep -v grep | awk '{print $2}' | xargs sudo kill -9
sudo systemctl start hydroclaude-backend

# 数据库快速恢复
# psql $DATABASE_URL < /backups/database/latest.sql
```

---

## 📞 支持和反馈

如有问题，请联系：
- 📧 Email: support@hydroclaude.com
- 📱 电话: ____________
- 💬 Slack: #hydroclaude-ops

---

## 📚 相关文档

- [部署检查清单](./DEPLOYMENT_CHECKLIST.md)
- [测试执行指南](./TEST_EXECUTION_GUIDE.md)
- [最终测试报告](./FINAL_COMPREHENSIVE_REPORT.md)

---

**保持系统健康运行！** 🚀

---

**文档维护**: HydroClaude Development Team  
**版本**: v1.0  
**最后更新**: 2025-11-12
