# HydroClaude Deployment Guide

**Version**: v1.3.0
**Last Updated**: 2025-11-11
**Target Audience**: System administrators, DevOps engineers

This guide provides comprehensive deployment instructions for HydroClaude in various environments.

---

## Table of Contents

- [Deployment Overview](#deployment-overview)
- [Development Deployment](#development-deployment)
- [Production Deployment](#production-deployment)
- [Docker Deployment](#docker-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Security Considerations](#security-considerations)
- [Monitoring & Logging](#monitoring--logging)
- [Backup & Recovery](#backup--recovery)
- [Scaling & Performance](#scaling--performance)
- [Troubleshooting](#troubleshooting)

---

## Deployment Overview

### Deployment Types

| Type | Use Case | Complexity | Multi-User | Security |
|------|----------|------------|------------|----------|
| **Development** | Local testing | Low | No | Basic |
| **Production (Single)** | Internal use | Medium | No | Medium |
| **Docker** | Containerized | Medium | No | Medium |
| **Cloud** | Scalable, public | High | Yes* | High |

*Multi-user features planned for v2.0

### Architecture

```
┌─────────────────────────────────────────┐
│          Client Browser                 │
│     (http://your-domain.com)           │
└────────────┬────────────────────────────┘
             │
             │ HTTP/HTTPS
             │
┌────────────▼────────────────────────────┐
│       Frontend Server (React)           │
│        Port 5173 or 80/443              │
│     Serves static files + SPA           │
└────────────┬────────────────────────────┘
             │
             │ API Calls
             │
┌────────────▼────────────────────────────┐
│      Backend API (FastAPI)              │
│           Port 8000                     │
│   ┌──────────────────────────────┐     │
│   │  API Gateway                 │     │
│   │  - Validation                │     │
│   │  - Task Management           │     │
│   └──────────┬───────────────────┘     │
│              │                          │
│   ┌──────────▼───────────────────┐     │
│   │  Hydraulic Solver Core       │     │
│   │  - Godunov FVM               │     │
│   │  - HLL Riemann Solver        │     │
│   │  - Numba JIT                 │     │
│   └──────────────────────────────┘     │
└─────────────────────────────────────────┘
```

---

## Development Deployment

### Quick Start (Local Development)

**Prerequisites**:
- Python 3.8+
- Node.js 16+
- Git

**Step 1: Clone and Setup**

```bash
# Clone repository
git clone https://github.com/YOUR_ORG/HydroClaude.git
cd HydroClaude

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd web/frontend
npm install
cd ../..
```

**Step 2: Start Services**

```bash
# Terminal 1: Start backend
cd web/backend
./start_server.sh

# Terminal 2: Start frontend
cd web/frontend
npm run dev
```

**Step 3: Verify**

```bash
# Test backend
curl http://localhost:8000/health
# Expected: {"status":"healthy"}

# Test frontend
# Open browser: http://localhost:5173
```

**Step 4: Run Tests**

```bash
# Verify installation
python web/verify_installation.py

# Run test suites
python web/test_stable_workflow.py
python web/test_error_handling.py
```

---

## Production Deployment

### Production Checklist

Before deploying to production:

- [ ] All tests passing (100%)
- [ ] Configuration validated
- [ ] Security hardening applied
- [ ] Monitoring configured
- [ ] Backup strategy in place
- [ ] Rollback plan documented
- [ ] Performance testing completed
- [ ] Documentation up to date

### Option 1: Systemd Service (Linux)

**Backend Service**

Create `/etc/systemd/system/hydroclaude-backend.service`:

```ini
[Unit]
Description=HydroClaude Backend API
After=network.target

[Service]
Type=simple
User=hydroclaude
WorkingDirectory=/opt/hydroclaude/web/backend
Environment="PATH=/opt/hydroclaude/venv/bin"
ExecStart=/opt/hydroclaude/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

**Enable and start**:

```bash
sudo systemctl daemon-reload
sudo systemctl enable hydroclaude-backend
sudo systemctl start hydroclaude-backend
sudo systemctl status hydroclaude-backend
```

**Frontend Service (using nginx)**

Build production frontend:

```bash
cd web/frontend
npm run build
# Creates dist/ directory
```

Copy to nginx directory:

```bash
sudo cp -r dist/* /var/www/hydroclaude/
```

Nginx configuration (`/etc/nginx/sites-available/hydroclaude`):

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        root /var/www/hydroclaude;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Backend API proxy
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support (future)
    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable and restart nginx:

```bash
sudo ln -s /etc/nginx/sites-available/hydroclaude /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

### Option 2: Supervisor (Alternative to systemd)

Install supervisor:

```bash
sudo apt-get install supervisor
```

Configuration (`/etc/supervisor/conf.d/hydroclaude.conf`):

```ini
[program:hydroclaude-backend]
command=/opt/hydroclaude/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
directory=/opt/hydroclaude/web/backend
user=hydroclaude
autostart=true
autorestart=true
stderr_logfile=/var/log/hydroclaude/backend.err.log
stdout_logfile=/var/log/hydroclaude/backend.out.log
```

Start:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start hydroclaude-backend
```

---

## Docker Deployment

### Dockerfile (Backend)

Create `web/backend/Dockerfile`:

```dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Dockerfile (Frontend)

Create `web/frontend/Dockerfile`:

```dockerfile
# Build stage
FROM node:16-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### docker-compose.yml

Create `docker-compose.yml` in project root:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./web/backend
      dockerfile: Dockerfile
    container_name: hydroclaude-backend
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
    volumes:
      - ./web/backend:/app
      - backend-data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  frontend:
    build:
      context: ./web/frontend
      dockerfile: Dockerfile
    container_name: hydroclaude-frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  backend-data:
```

### Deploy with Docker Compose

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

---

## Cloud Deployment

### AWS Deployment

**Architecture**:
```
Internet → ALB → ECS (Backend + Frontend) → S3 (results storage)
```

**Step 1: Prepare Docker Images**

```bash
# Build and push to ECR
aws ecr create-repository --repository-name hydroclaude-backend
aws ecr create-repository --repository-name hydroclaude-frontend

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Build and push backend
docker build -t hydroclaude-backend web/backend/
docker tag hydroclaude-backend:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/hydroclaude-backend:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/hydroclaude-backend:latest

# Build and push frontend
docker build -t hydroclaude-frontend web/frontend/
docker tag hydroclaude-frontend:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/hydroclaude-frontend:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/hydroclaude-frontend:latest
```

**Step 2: Create ECS Task Definition**

See AWS ECS documentation for creating task definitions using your pushed images.

**Step 3: Configure Application Load Balancer**

- Route `/api/*` to backend service
- Route `/*` to frontend service
- Enable HTTPS with ACM certificate

---

### Azure Deployment

**Option: Azure App Service**

```bash
# Create resource group
az group create --name hydroclaude-rg --location eastus

# Create App Service plan
az appservice plan create --name hydroclaude-plan --resource-group hydroclaude-rg --sku B1 --is-linux

# Create backend web app
az webapp create --resource-group hydroclaude-rg --plan hydroclaude-plan --name hydroclaude-backend --runtime "PYTHON|3.9"

# Deploy backend
cd web/backend
az webapp up --resource-group hydroclaude-rg --name hydroclaude-backend

# Create frontend web app
az webapp create --resource-group hydroclaude-rg --plan hydroclaude-plan --name hydroclaude-frontend --runtime "NODE|16-lts"

# Deploy frontend
cd web/frontend
npm run build
az webapp deployment source config-zip --resource-group hydroclaude-rg --name hydroclaude-frontend --src dist.zip
```

---

### Google Cloud Platform

**Option: Cloud Run**

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/YOUR_PROJECT/hydroclaude-backend web/backend/
gcloud builds submit --tag gcr.io/YOUR_PROJECT/hydroclaude-frontend web/frontend/

# Deploy backend
gcloud run deploy hydroclaude-backend \
  --image gcr.io/YOUR_PROJECT/hydroclaude-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated

# Deploy frontend
gcloud run deploy hydroclaude-frontend \
  --image gcr.io/YOUR_PROJECT/hydroclaude-frontend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

## Security Considerations

### Production Security Checklist

#### Application Security

- [ ] **HTTPS Enabled**: Use TLS/SSL certificates (Let's Encrypt recommended)
- [ ] **CORS Configured**: Restrict to your domain only
- [ ] **Input Validation**: Enabled (v1.3.0 has 30+ validation rules)
- [ ] **Rate Limiting**: Implement API rate limiting (future v2.0 feature)
- [ ] **Authentication**: Implement for multi-user (planned v2.0)

#### Network Security

- [ ] **Firewall**: Only expose ports 80/443
- [ ] **Private Backend**: Backend on port 8000 not publicly accessible
- [ ] **VPC/Security Groups**: Properly configured (cloud deployments)

#### System Security

- [ ] **OS Updates**: Keep system packages updated
- [ ] **Least Privilege**: Run services as non-root user
- [ ] **File Permissions**: Restrict write access
- [ ] **Secrets Management**: Use environment variables, not hardcoded

### HTTPS Setup (Let's Encrypt)

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo certbot renew --dry-run
```

### Environment Variables

Create `.env` file (DO NOT commit to git):

```bash
# Backend configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# Security
ALLOWED_ORIGINS=https://your-domain.com
API_KEY_REQUIRED=false  # Enable in v2.0

# Performance
MAX_WORKERS=4
TIMEOUT=300
```

Load in application:

```python
from dotenv import load_dotenv
import os

load_dotenv()

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
```

---

## Monitoring & Logging

### Log Configuration

**Backend Logging** (`web/backend/main.py`):

```python
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
handler = RotatingFileHandler(
    'logs/hydroclaude.log',
    maxBytes=10_000_000,  # 10 MB
    backupCount=5
)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)

logger = logging.getLogger("hydroclaude")
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

### Monitoring Tools

**Option 1: Simple Log Monitoring**

```bash
# Monitor backend logs
tail -f /var/log/hydroclaude/backend.log

# Check for errors
grep ERROR /var/log/hydroclaude/backend.log
```

**Option 2: Prometheus + Grafana** (Advanced)

Install Prometheus exporter:

```bash
pip install prometheus-fastapi-instrumentator
```

Add to `main.py`:

```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

# Instrument app
Instrumentator().instrument(app).expose(app)
```

Access metrics at: `http://localhost:8000/metrics`

**Option 3: Cloud Monitoring**

- **AWS**: CloudWatch
- **Azure**: Application Insights
- **GCP**: Cloud Monitoring

---

## Backup & Recovery

### Backup Strategy

**What to Backup**:
1. Configuration files
2. Simulation results (if persisting)
3. User data (v2.0+)
4. Database (v2.0+)

**Backup Script** (`backup.sh`):

```bash
#!/bin/bash

BACKUP_DIR="/backup/hydroclaude"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup configurations
tar -czf $BACKUP_DIR/configs_$DATE.tar.gz web/config_templates/

# Backup results (if applicable)
if [ -d "web/backend/results" ]; then
    tar -czf $BACKUP_DIR/results_$DATE.tar.gz web/backend/results/
fi

# Keep only last 7 days
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
```

**Automate with cron**:

```bash
# Run daily at 2 AM
0 2 * * * /opt/hydroclaude/backup.sh
```

### Recovery Procedure

```bash
# Stop services
sudo systemctl stop hydroclaude-backend

# Restore from backup
tar -xzf /backup/hydroclaude/configs_YYYYMMDD_HHMMSS.tar.gz -C /opt/hydroclaude/

# Restart services
sudo systemctl start hydroclaude-backend
sudo systemctl status hydroclaude-backend
```

---

## Scaling & Performance

### Performance Tuning

**Backend**:

```python
# In main.py
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        workers=4,  # Number of worker processes
        log_level="info"
    )
```

**Nginx Caching**:

```nginx
# Cache static files
location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### Horizontal Scaling (v2.0+)

**Future**: Distributed task queue with Celery + Redis

```
┌──────────┐    ┌──────────┐    ┌──────────┐
│ Worker 1 │    │ Worker 2 │    │ Worker N │
└─────┬────┘    └─────┬────┘    └─────┬────┘
      │               │               │
      └───────────────┴───────────────┘
                      │
                ┌─────▼─────┐
                │   Redis   │
                │   Queue   │
                └───────────┘
```

---

## Troubleshooting

### Common Deployment Issues

#### Issue: "Port already in use"

```bash
# Find process using port
sudo lsof -i :8000
sudo lsof -i :5173

# Kill process
sudo kill -9 PID

# Or change port in configuration
```

#### Issue: "Permission denied"

```bash
# Fix ownership
sudo chown -R hydroclaude:hydroclaude /opt/hydroclaude

# Fix permissions
chmod +x web/backend/start_server.sh
```

#### Issue: "Module not found"

```bash
# Ensure virtual environment activated
source /opt/hydroclaude/venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

#### Issue: "Nginx 502 Bad Gateway"

```bash
# Check backend is running
curl http://localhost:8000/health

# Check nginx error log
sudo tail -f /var/log/nginx/error.log

# Verify proxy settings in nginx config
```

### Health Check Script

Create `health_check.sh`:

```bash
#!/bin/bash

# Check backend
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ Backend: Healthy"
else
    echo "✗ Backend: Down"
    exit 1
fi

# Check frontend
if curl -f http://localhost > /dev/null 2>&1; then
    echo "✓ Frontend: Healthy"
else
    echo "✗ Frontend: Down"
    exit 1
fi

echo "All services healthy"
```

Run periodically:

```bash
# Add to crontab (every 5 minutes)
*/5 * * * * /opt/hydroclaude/health_check.sh || /opt/hydroclaude/restart_services.sh
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Code tested locally (100% tests passing)
- [ ] Configuration files prepared
- [ ] Environment variables configured
- [ ] SSL certificates obtained
- [ ] Firewall rules configured
- [ ] Backup strategy in place

### Deployment

- [ ] Deploy backend
- [ ] Deploy frontend
- [ ] Configure reverse proxy (nginx/ALB)
- [ ] Enable HTTPS
- [ ] Test API endpoints
- [ ] Test web interface

### Post-Deployment

- [ ] Monitor logs for errors
- [ ] Run health checks
- [ ] Performance testing
- [ ] Security scan
- [ ] Document deployment
- [ ] Train users

---

## Additional Resources

- **Quick Start**: `README.md`
- **Configuration**: `PARAMETER_SELECTION_GUIDE.md`
- **Troubleshooting**: `FAQ.md`
- **Security**: Follow OWASP best practices
- **Docker**: https://docs.docker.com
- **Kubernetes**: For large-scale deployments (future)

---

**Last Updated**: 2025-11-11
**Version**: v1.3.0
**Deployment Guide Version**: 1.0
