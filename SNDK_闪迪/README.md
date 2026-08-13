# 闪迪 (SNDK) 分析

## 股票信息
- **股票代码**: SNDK
- **公司名称**: SanDisk Corporation
- **行业**: 数据存储/闪存
- **主要产品**: 闪存卡、U盘、SSD固态硬盘

## 快速获取数据

```python
import sys
sys.path.insert(0, '..')

from utils.data_fetcher import fetch_stock_data, USStockDataFetcher

# 获取闪迪股票数据
df = fetch_stock_data('SNDK', period='2y')
print(f"获取到 {len(df)} 条数据")

# 保存到当前目录
fetcher = USStockDataFetcher(data_dir='.')
df = fetcher.get_stock_data('SNDK', period='2y')
fetcher.save_data(df, 'SNDK')
```

## 文件说明
- `SNDK_data.xlsx` - 闪迪股票历史数据（Open/High/Low/Close保留3位小数）
- `SNDK_analysis.ipynb` - 分析笔记本（可选）
- `SNDK_strategy.py` - 策略文件（可选）
