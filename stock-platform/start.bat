@echo off
echo ================================
echo  量化交易平台启动脚本
echo ================================

REM 启动后端
echo.
echo [1/2] 启动后端服务...
cd backend
start "Backend" cmd /k "pip install -r requirements.txt && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

REM 等待后端启动
echo 等待后端启动...
timeout /t 5 /nobreak > nul

REM 启动前端
echo.
echo [2/2] 启动前端服务...
cd ../frontend
start "Frontend" cmd /k "npm install && npm run dev"

echo.
echo ================================
echo  服务启动完成！
echo ================================
echo.
echo 后端API文档: http://localhost:8000/docs
echo 前端界面:    http://localhost:3000
echo.
echo 按任意键退出...
pause > nul
