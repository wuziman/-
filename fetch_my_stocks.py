"""
批量获取自选股数据
将数据分别保存到对应的文件夹
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.data_fetcher import USStockDataFetcher
from datetime import datetime


def fetch_all_stocks(period='2y'):
    """
    批量获取所有自选股数据

    参数:
        period: 数据周期，默认2年
    """
    print("="*60)
    print("  批量获取自选股数据")
    print("="*60)

    # 定义股票配置
    stocks = [
        {
            'symbol': 'MU',
            'name': '美光科技',
            'folder': 'MU_美光'
        },
        {
            'symbol': 'SNDK',
            'name': '闪迪',
            'folder': 'SNDK_闪迪'
        },
        {
            'symbol': 'SOXL',
            'name': '三倍做多半导体ETF',
            'folder': 'SOXL_半导体ETF'
        },
        {
            'symbol': 'NKE',
            'name': '耐克',
            'folder': 'NKE_耐克'
        },
        {
            'symbol': 'AXTI',
            'name': 'AXT光通信原材料',
            'folder': 'AXT_光通信原材料'
        },
        {
            'symbol': 'AAOI',
            'name': '祥茂光电光模块',
            'folder': 'AAOI_光模块'
        },
        {
            'symbol': 'LITE',
            'name': 'Lumentum光通信器件',
            'folder': 'LITE_光通信器件'
        },
        {
            'symbol': 'COHR',
            'name': 'Coherent光学材料',
            'folder': 'COHR_光学材料'
        },
        {
            'symbol': 'NVDA',
            'name': '英伟达',
            'folder': 'NVDA_英伟达'
        },
        {
            'symbol': 'AVGO',
            'name': '博通',
            'folder': 'AVGO_博通'
        }
    ]

    # 获取项目根目录
    project_root = os.path.dirname(os.path.abspath(__file__))

    results = []

    for stock in stocks:
        print(f"\n{'─'*60}")
        print(f"正在获取: {stock['name']} ({stock['symbol']})")
        print(f"{'─'*60}")

        # 构建保存路径
        save_dir = os.path.join(project_root, stock['folder'])
        os.makedirs(save_dir, exist_ok=True)

        # 创建数据获取器
        fetcher = USStockDataFetcher(data_dir=save_dir)

        # 获取数据
        df = fetcher.get_stock_data(stock['symbol'], period=period)

        if df.empty:
            print(f"[FAIL] {stock['symbol']}: 无法获取数据")
            results.append({
                'symbol': stock['symbol'],
                'name': stock['name'],
                'status': '失败',
                'rows': 0
            })
            continue

        # 保存数据
        filepath = fetcher.save_data(df, stock['symbol'])

        # 统计信息
        start_date = df.index[0].strftime('%Y-%m-%d')
        end_date = df.index[-1].strftime('%Y-%m-%d')
        start_price = df['Close'].iloc[0]
        end_price = df['Close'].iloc[-1]
        return_pct = (end_price / start_price - 1) * 100

        print(f"\n[OK] {stock['symbol']}:")
        print(f"   数据条数: {len(df)}")
        print(f"   时间范围: {start_date} 到 {end_date}")
        print(f"   起始价格: ${start_price:.2f}")
        print(f"   结束价格: ${end_price:.2f}")
        print(f"   期间涨幅: {return_pct:.2f}%")
        print(f"   保存位置: {filepath}")

        results.append({
            'symbol': stock['symbol'],
            'name': stock['name'],
            'status': '成功',
            'rows': len(df),
            'start_date': start_date,
            'end_date': end_date,
            'return_pct': return_pct
        })

    # 打印汇总
    print("\n" + "="*60)
    print("  汇总结果")
    print("="*60)
    print(f"\n{'股票':<10} {'名称':<20} {'状态':<8} {'数据量':<8} {'涨幅':<10}")
    print("-"*60)

    for r in results:
        status = r['status']
        rows = r.get('rows', 0)
        ret = f"{r.get('return_pct', 0):.2f}%" if 'return_pct' in r else "N/A"
        print(f"{r['symbol']:<10} {r['name']:<20} {status:<8} {rows:<8} {ret:<10}")

    print("="*60)

    return results


if __name__ == "__main__":
    # 可以修改period参数来获取不同周期的数据
    # '1mo', '3mo', '6mo', '1y', '2y', '5y'
    fetch_all_stocks(period='2y')
