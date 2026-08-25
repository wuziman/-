"""
每日报告服务
- 汇总自选股：双策略点位 + MACD状态 + 技术评分
- 生成企业微信markdown日报
- 通过webhook推送（支持dry_run预览）
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import requests
import pandas as pd

from .stock_service import StockService
from .tech_score import calculate_tech_score
from ..utils.indicators import calculate_all_indicators
from ..utils.market import detect_market


def _load_webhook() -> str:
    """企业微信webhook：环境变量优先，其次原项目config"""
    url = os.environ.get('WECHAT_WEBHOOK', '')
    if url:
        return url
    try:
        config_path = Path(__file__).resolve().parents[4] / 'config' / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f).get('wechat_webhook', '')
    except Exception:
        return ''


class ReportService:
    """每日报告服务"""

    def __init__(self):
        self.stock_service = StockService()

    # ============================================
    # 单只股票：三策略快照（轻量，不拉新闻）
    # ============================================
    def _stock_snapshot(self, stock_code: str, stock_name: str) -> Optional[Dict]:
        market = detect_market(stock_code)
        df = self.stock_service.get_stock_data(stock_code, market, period="3mo")
        if df is None or df.empty:
            return None

        df = calculate_all_indicators(df)
        latest = df.iloc[-1]
        current = float(latest['Close'])
        rsi = latest.get('RSI', 50)
        rsi = float(rsi) if pd.notna(rsi) else 50.0
        ma20 = latest.get('MA20', current)
        ma20 = float(ma20) if pd.notna(ma20) else current * 0.95
        bb_lower = latest.get('BB_Lower', current * 0.9)
        bb_lower = float(bb_lower) if pd.notna(bb_lower) else current * 0.9

        # 线性策略
        if ma20 < current:
            linear_buy = current - 0.5 * (current - ma20)
        else:
            linear_buy = current * 0.95
        linear_buy = min(linear_buy, current * 0.95)

        # 非线性策略
        nonlinear_buy = bb_lower if rsi < 30 else ma20

        # MACD状态与持续天数
        macd = latest.get('MACD')
        signal = latest.get('MACD_Signal')
        if pd.notna(macd) and pd.notna(signal):
            is_golden = float(macd) > float(signal)
            above = df['MACD'] > df['MACD_Signal']
            days = 0
            for v in reversed(above.values.tolist()):
                if bool(v) == is_golden:
                    days += 1
                else:
                    break
            macd_state = f"{'🟢金叉' if is_golden else '🔴死叉'}{days}天"
            macd_golden = is_golden
        else:
            macd_state = '未知'
            macd_golden = None

        # 技术评分（调用与分析服务共享的同一实现，含布林带调整）
        tech, _ = calculate_tech_score(latest)

        if tech >= 8:
            rec, color = '强烈买入', 'info'
        elif tech >= 6.5:
            rec, color = '买入', 'info'
        elif tech >= 5:
            rec, color = '观望', 'comment'
        else:
            rec, color = '谨慎', 'warning'

        return {
            'code': stock_code,
            'name': stock_name,
            'market': market,
            'price': round(current, 2),
            'rsi': round(rsi, 1),
            'tech': round(tech, 1),
            'rec': rec,
            'color': color,
            'macd_state': macd_state,
            'macd_golden': macd_golden,
            # MACD策略操作参考
            'macd_add': round(ma20, 2) if macd_golden else None,          # 金叉：回踩MA20加仓参考
            'macd_watch': round(bb_lower, 2) if macd_golden is False else None,  # 死叉：关注布林下轨
            'macd_stop': round(current * 0.92, 2),                        # 纪律止损-8%
            'linear': {
                'buy': round(linear_buy, 2),
                'profit': round(linear_buy * 1.15, 2),
                'stop': round(linear_buy * 0.92, 2),
                'distance': round((current - linear_buy) / current * 100, 1),
            },
            'nonlinear': {
                'buy': round(nonlinear_buy, 2),
                'profit': round(nonlinear_buy * 1.46, 2),
                'stop': round(nonlinear_buy * 0.92, 2),
                'distance': round((current - nonlinear_buy) / current * 100, 1),
            },
        }

    # ============================================
    # 生成日报（企业微信markdown格式）
    # ============================================
    def generate_daily_report(self, watchlist: List[Dict]) -> Dict:
        """watchlist: [{stock_code, stock_name}] → {report, snapshots, failed}"""
        snapshots: List[Dict] = []
        failed: List[str] = []

        for item in watchlist:
            try:
                snap = self._stock_snapshot(item['stock_code'], item['stock_name'])
                if snap:
                    snapshots.append(snap)
                else:
                    failed.append(f"{item['stock_code']} {item['stock_name']}")
            except Exception as e:
                print(f"快照失败 {item['stock_code']}: {e}")
                failed.append(f"{item['stock_code']} {item['stock_name']}")

        # 按技术分排序
        snapshots.sort(key=lambda s: s['tech'], reverse=True)

        now = datetime.now()
        lines = [
            f"**📈 股票日报·三策略版** {now.strftime('%m-%d %H:%M')}",
            f"> 自选{len(snapshots)}只 | 按技术评分排序",
            '',
        ]
        for i, s in enumerate(snapshots, 1):
            price_str = f"¥{s['price']}" if s['market'] == 'A' else f"${s['price']}"
            lines.append(
                f"**{i}. {s['name']} {s['code']}** <font color=\"{s['color']}\">{s['rec']}</font> {s['tech']}分"
            )
            lines.append(
                f"现价{price_str} RSI{s['rsi']} MACD:{s['macd_state']}"
            )
            lines.append(
                f"线性: 买{s['linear']['buy']}({s['linear']['distance']:+.1f}%) "
                f"盈{s['linear']['profit']} 损{s['linear']['stop']}"
            )
            lines.append(
                f"非线性: 买{s['nonlinear']['buy']}({s['nonlinear']['distance']:+.1f}%) "
                f"盈{s['nonlinear']['profit']} 损{s['nonlinear']['stop']}"
            )
            # MACD策略操作参考
            if s.get('macd_golden'):
                lines.append(
                    f"MACD: {s['macd_state']} ✅持有 加仓MA20 {s['macd_add']} "
                    f"离场=死叉 损{s['macd_stop']}"
                )
            elif s.get('macd_golden') is False:
                lines.append(
                    f"MACD: {s['macd_state']} ⏳观望 关注下轨{s['macd_watch']} "
                    f"入场=金叉 损{s['macd_stop']}"
                )
            else:
                lines.append("MACD: 数据不足")
            lines.append('')

        if failed:
            lines.append(f"⚠️ 数据缺失: {', '.join(failed)}")
        lines.append('> 仅供参考，投资有风险')

        report = '\n'.join(lines)
        return {
            'report': report,
            'snapshots': snapshots,
            'failed': failed,
            'generated_at': now.isoformat(),
            'char_count': len(report.encode('utf-8')),
        }

    # ============================================
    # 推送企业微信
    # ============================================
    def send_to_wechat(self, report: str) -> Dict:
        webhook = _load_webhook()
        if not webhook:
            return {'sent': False, 'error': '未配置企业微信Webhook（config/config.json的wechat_webhook）'}

        # 企业微信markdown上限4096字节；中文每字3字节，必须按字节裁剪而非字符切片
        payload_report = report
        if len(report.encode('utf-8')) > 4000:
            payload_report = report
            while len(payload_report.encode('utf-8')) > 3800:
                payload_report = payload_report[:-200]
            payload_report += '\n> ...(报告过长，已截断)'

        try:
            resp = requests.post(webhook, json={
                'msgtype': 'markdown',
                'markdown': {'content': payload_report}
            }, timeout=10)
            data = resp.json()
            if resp.status_code == 200 and data.get('errcode') == 0:
                return {'sent': True}
            return {'sent': False, 'error': f"HTTP {resp.status_code}: {data}"}
        except Exception as e:
            return {'sent': False, 'error': str(e)}
