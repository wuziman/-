@echo off
echo ================================
echo  量化交易平台 - 快速安装
echo ================================

echo.
echo [1/3] 安装后端依赖...
cd backend
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 后端依赖安装失败！
    pause
    exit /b 1
)
echo 后端依赖安装完成！

echo.
echo [2/3] 安装前端依赖...
cd ../frontend
call npm install
if %errorlevel% neq 0 (
    echo 前端依赖安装失败！
    pause
    exit /b 1
)
echo 前端依赖安装完成！

echo.
echo [3/3] 安装完成！
echo.
echo ================================
echo  安装完成，可以启动服务了！
echo ================================
echo.
echo 运行 start.bat 启动服务
echo.
pause
