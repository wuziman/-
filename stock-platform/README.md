# 📈 量化交易平台

支持A股和美股的四维度量化分析系统，包含完整前后端。

## 技术栈

- **前端**：React + TypeScript + Ant Design + ECharts
- **后端**：Python FastAPI + SQLAlchemy
- **数据库**：SQLite
- **数据源**：AKShare（A股）+ YFinance（美股）

## 功能特性

### 1. 股票分析
- 四维度分析：技术面、消息面、宏观面、事件驱动
- 实时K线图表
- 买卖点位推荐
- 自选股管理

### 2. 策略回测
- 线性策略（斐波那契回撤）
- 非线性策略（均线+RSI）
- 双均线交叉
- MACD金叉死叉

### 3. 持仓管理
- 实时盈亏跟踪
- 止盈止损设置
- 仓位分析

## 快速开始

### 1. 后端启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API文档：http://localhost:8000/docs

### 2. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问：http://localhost:3000

## 项目结构

```
stock-platform/
├── backend/                    # FastAPI后端
│   ├── app/
│   │   ├── main.py            # 入口
│   │   ├── models.py          # 数据库模型
│   │   ├── schemas.py         # 数据验证
│   │   ├── routers/           # API路由
│   │   └── services/          # 业务逻辑
│   └── requirements.txt
│
├── frontend/                   # React前端
│   ├── src/
│   │   ├── components/        # 组件
│   │   ├── pages/             # 页面
│   │   └── services/          # API调用
│   └── package.json
│
└── README.md
```

## API接口

### 股票相关
- `GET /api/stocks/search?q=xxx` - 搜索股票
- `GET /api/stocks/{code}/quote` - 获取实时行情
- `GET /api/stocks/{code}/history` - 获取历史数据
- `GET /api/stocks/watchlist` - 获取自选股
- `POST /api/stocks/watchlist` - 添加自选股

### 分析相关
- `POST /api/analysis` - 综合分析
- `GET /api/analysis/history` - 分析历史

### 回测相关
- `GET /api/backtest/strategies` - 获取策略列表
- `POST /api/backtest` - 运行回测

### 持仓相关
- `GET /api/portfolio` - 获取持仓
- `POST /api/portfolio` - 添加持仓
- `PUT /api/portfolio/{id}` - 更新持仓
- `DELETE /api/portfolio/{id}` - 删除持仓

## 使用说明

### 股票代码格式

**美股**：直接使用代码，如 `AAPL`, `MU`, `NVDA`

**A股**：6位数字代码，如 `000001`, `600000`

### 策略说明

| 策略 | 买入条件 | 卖出条件 | 适用场景 |
|------|----------|----------|----------|
| 线性策略 | 价格回调50%位置 | +15%止盈 / -8%止损 | 趋势回调 |
| 非线性策略 | RSI超卖+均线支撑 | +46%止盈 / -8%止损 | 超卖反弹 |
| 双均线交叉 | MA20上穿MA50 | MA20下穿MA50 | 趋势跟踪 |
| MACD策略 | MACD金叉 | MACD死叉 | 动量交易 |

## 风险提示

⚠️ 本系统仅供学习研究使用，不构成投资建议。股市有风险，投资需谨慎。

## License

MIT
