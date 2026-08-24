#!/bin/bash

echo "================================"
echo "  量化交易平台 - 快速安装"
echo "================================"

echo ""
echo "[1/3] 安装后端依赖..."
cd backend
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "后端依赖安装失败！"
    exit 1
fi
echo "后端依赖安装完成！"

echo ""
echo "[2/3] 安装前端依赖..."
cd ../frontend
npm install
if [ $? -ne 0 ]; then
    echo "前端依赖安装失败！"
    exit 1
fi
echo "前端依赖安装完成！"

echo ""
echo "[3/3] 安装完成！"
echo ""
echo "================================"
echo "  安装完成，可以启动服务了！"
echo "================================"
echo ""
echo "运行 start.sh 启动服务"
