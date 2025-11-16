@echo off
REM HydroClaude Web端到端全量测试脚本（Windows）
REM 使用方法: run_full_test.bat [案例数量]

echo ================================================================
echo HydroClaude Web端到端测试 - Windows中文环境
echo ================================================================
echo.

REM 检查参数
set MAX_CASES=10
if not "%1"=="" set MAX_CASES=%1

echo 测试配置:
echo   - 最大案例数: %MAX_CASES%
echo   - 浏览器: Chromium (中文)
echo   - 截图: 启用
echo.

REM 检查环境
echo [1/5] 检查环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ❌ Python未安装
    pause
    exit /b 1
)
echo   ✅ Python已安装

playwright --version >nul 2>&1
if errorlevel 1 (
    echo   ⚠️  Playwright未安装，正在安装...
    pip install playwright
    playwright install chromium
)
echo   ✅ Playwright已安装

REM 检查Web应用
echo.
echo [2/5] 检查Web应用...
curl -s http://localhost:5173 >nul 2>&1
if errorlevel 1 (
    echo   ❌ Web应用未运行
    echo   请先启动: cd webapp ^&^& npm run dev
    pause
    exit /b 1
)
echo   ✅ Web应用运行中

REM 转换测试案例
echo.
echo [3/5] 转换测试案例...
python convert_test_cases.py
if errorlevel 1 (
    echo   ❌ 转换失败
    pause
    exit /b 1
)
echo   ✅ 转换完成

REM 运行测试
echo.
echo [4/5] 运行端到端测试...
echo   正在测试 %MAX_CASES% 个案例，请稍候...
echo.
python test_web_e2e.py --max-cases %MAX_CASES%
if errorlevel 1 (
    echo.
    echo   ⚠️  测试过程中出现错误
    echo   查看报告了解详情
) else (
    echo.
    echo   ✅ 测试完成
)

REM 打开报告
echo.
echo [5/5] 生成报告...
for /f "delims=" %%i in ('dir /b /od reports\test_report_*.html') do set LATEST_REPORT=%%i
if exist "reports\%LATEST_REPORT%" (
    echo   ✅ 报告已生成: reports\%LATEST_REPORT%
    echo.
    echo 是否打开测试报告? (Y/N)
    set /p OPEN_REPORT=
    if /i "%OPEN_REPORT%"=="Y" (
        start "" "reports\%LATEST_REPORT%"
    )
) else (
    echo   ⚠️  未找到报告文件
)

echo.
echo ================================================================
echo 测试完成！
echo ================================================================
echo.
echo 查看结果:
echo   - HTML报告: reports\%LATEST_REPORT%
echo   - JSON报告: reports\test_report_*.json
echo   - 截图: screenshots\
echo.
pause
