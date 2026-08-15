# 🚀 量化投资分析系统 - 配置指南

## 📋 系统概述

本系统是一个四维度股票分析工具，包含：
- **技术面分析**：RSI、MACD、均线、布林带
- **消息面分析**：NewsAPI + 网页抓取
- **宏观面分析**：FRED API + 网页抓取
- **事件驱动分析**：财经日历

系统每天自动运行，生成分析报告并推送到企业微信。

---

## 🔧 配置步骤

### 1. 配置API Keys

在GitHub仓库的 **Settings → Secrets and variables → Actions** 中添加以下Secrets：

| Secret名称 | 说明 | 获取方式 |
|------------|------|----------|
| `WECHAT_WEBHOOK` | 企业微信Webhook URL | 企业微信群机器人 |
| `NEWSAPI_KEY` | NewsAPI Key | https://newsapi.org/ |
| `FRED_API_KEY` | FRED API Key | https://fred.stlouisfed.org/ |

### 2. 配置企业微信机器人

1. 在企业微信群中添加机器人
2. 获取Webhook URL
3. 将URL添加到GitHub Secrets

### 3. 获取NewsAPI Key

1. 访问 https://newsapi.org/
2. 注册账号
3. 获取API Key
4. 将Key添加到GitHub Secrets

### 4. 获取FRED API Key

1. 访问 https://fred.stlouisfed.org/
2. 注册账号
3. 获取API Key
4. 将Key添加到GitHub Secrets

---

## 📊 股票列表

系统默认分析以下股票：

| 代码 | 名称 | 行业 |
|------|------|------|
| MU | 美光科技 | 半导体/存储芯片 |
| SNDK | 闪迪 | 数据存储/闪存 |
| SOXL | 三倍做多半导体ETF | 杠杆ETF |
| NKE | 耐克 | 运动服饰/消费品 |
| AXTI | AXT光通信原材料 | 光通信/半导体材料 |
| AAOI | 祥茂光电光模块 | 光通信/光模块 |
| LITE | Lumentum光通信器件 | 光通信/激光器 |
| COHR | Coherent光学材料 | 光通信/光学材料 |

**修改股票列表**：编辑 `config/config.json` 文件

---

## ⏰ 定时任务

系统每天北京时间早上9点自动运行（GitHub Actions）。

**手动触发**：在GitHub仓库的Actions页面，点击"Daily Stock Analysis" → "Run workflow"

---

## 📱 报告格式

系统生成的报告包含：

### 1. 推荐排序
按综合评分从高到低排序，显示：
- 推荐等级（强烈推荐/推荐/中性/谨慎/不推荐）
- 建议买入价格
- 止盈位
- 止损位

### 2. 详细分析
每只股票的四个维度评分：
- 技术面评分
- 消息面评分
- 宏观面评分
- 事件驱动评分

---

## 🛠️ 本地测试

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置本地环境变量
```bash
# Windows PowerShell
$env:NEWSAPI_KEY="your_newsapi_key"
$env:FRED_API_KEY="your_fred_key"
$env:WECHAT_WEBHOOK="your_wechat_webhook"
```

### 3. 运行分析
```bash
python daily_stock_report.py
```

---

## 🔍 故障排查

### 问题1：API调用失败
- 检查API Key是否正确
- 检查网络连接
- 检查API额度是否用完

### 问题2：企业微信通知失败
- 检查Webhook URL是否正确
- 检查机器人是否被禁用
- 检查报告长度是否超过限制

### 问题3：股票数据获取失败
- 检查股票代码是否正确
- 检查Yahoo Finance是否可访问

---

## 📝 更新日志

### 2026-08-15
- ✅ 新增四维度分析（技术面、消息面、宏观面、事件驱动）
- ✅ 新增NewsAPI集成
- ✅ 新增FRED API集成
- ✅ 新增网页抓取支持
- ✅ 新增交叉验证机制
- ✅ 新增推荐排序功能
- ✅ 新增价格点位计算（止盈止损）

---

## ⚠️ 免责声明

本系统仅供学习和参考使用，不构成任何投资建议。投资有风险，入市需谨慎。

---

## 📞 联系方式

如有问题，请在GitHub仓库中提交Issue。
