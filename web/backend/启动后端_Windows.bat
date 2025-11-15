@echo off
chcp 65001 >nul
REM ===================================================================
REM  HydroClaude Web 后端服务器 - Windows启动脚本
REM  支持中文环境
REM ===================================================================

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║       HydroClaude Web 后端服务器 (Windows)               ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

REM 设置UTF-8编码环境变量
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set PYTHONPATH=%CD%\..;%PYTHONPATH%

echo [信息] 当前目录: %CD%
echo [信息] Python路径: %PYTHONPATH%
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到Python！请先安装Python 3.8+
    pause
    exit /b 1
)

echo [1/4] 检查Python环境...
python --version

REM 检查依赖
echo [2/4] 检查依赖包...
python -c "import fastapi, uvicorn" >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 缺少依赖，正在安装...
    pip install fastapi uvicorn[standard] -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo [3/4] 进入API网关目录...
cd api_gateway

echo [4/4] 启动服务器...
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  服务器地址:
echo    - API文档:   http://localhost:8000/api/docs
echo    - 健康检查:  http://localhost:8000/health
echo    - ReDoc:     http://localhost:8000/api/redoc
echo.
echo  按 Ctrl+C 停止服务器
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

python start_server_windows.py

pause
