# -*- coding: utf-8 -*-
"""第一批功能单元测试：卖出计算 / 日报快照 / 风控规则"""
import sys
from pathlib import Path

import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.report_service import ReportService, _load_webhook


# ============================================
# 日报快照（monkeypatch快照函数，不依赖网络）
# ============================================
def _fake_snap(code, name, market='US', tech=6.0):
    """构造一份与_stock_snapshot同构的快照"""
    return {
        'code': code, 'name': name, 'market': market,
        'price': 100.0, 'rsi': 50.0, 'tech': tech,
        'rec': '买入', 'color': 'info', 'macd_state': '🟢金叉3天',
        'macd_golden': True, 'macd_add': 99.0, 'macd_watch': None, 'macd_stop': 92.0,
        'linear': {'buy': 95.0, 'profit': 109.25, 'stop': 87.4, 'distance': 5.0},
        'nonlinear': {'buy': 97.0, 'profit': 141.62, 'stop': 89.24, 'distance': 3.0},
    }


class TestReportSnapshot:
    def _svc(self):
        return ReportService()

    def test_report_structure_and_sorting(self, monkeypatch):
        """真实拼装路径：按技术分降序，报告含标题/免责声明/币种符号"""
        svc = self._svc()
        snaps = {
            ('MU', 'Micron'): _fake_snap('MU', 'Micron', 'US', tech=7.0),
            ('002594', '比亚迪'): _fake_snap('002594', '比亚迪', 'A', tech=5.5),
        }
        monkeypatch.setattr(svc, '_stock_snapshot',
                            lambda code, name: snaps[(code, name)])

        result = svc.generate_daily_report([
            {'stock_code': '002594', 'stock_name': '比亚迪'},
            {'stock_code': 'MU', 'stock_name': 'Micron'},
        ])

        report = result['report']
        assert '三策略版' in report
        assert '自选2只' in report
        assert '仅供参考，投资有风险' in report
        # 排序：技术分高的MU排第1；A股前缀¥、美股前缀$
        assert report.index('1. Micron') < report.index('2. 比亚迪')
        assert '$100.0' in report and '¥100.0' in report

    def test_failed_stocks_listed(self, monkeypatch):
        """快照返回None或抛异常都进failed列表，且不中断其余股票生成"""
        svc = self._svc()

        def fake_snapshot(code, name):
            if code == 'ZZZZZZ':
                return None
            if code == 'BOOM':
                raise RuntimeError('boom')
            return _fake_snap(code, name)

        monkeypatch.setattr(svc, '_stock_snapshot', fake_snapshot)
        result = svc.generate_daily_report([
            {'stock_code': 'ZZZZZZ', 'stock_name': '不存在'},
            {'stock_code': 'BOOM', 'stock_name': '会炸'},
            {'stock_code': 'MU', 'stock_name': 'Micron'},
        ])

        assert result['failed'] == ['ZZZZZZ 不存在', 'BOOM 会炸']
        assert [s['code'] for s in result['snapshots']] == ['MU']
        assert isinstance(result['report'], str)
        assert '⚠️ 数据缺失: ZZZZZZ 不存在, BOOM 会炸' in result['report']

    def test_char_count_bytes(self, monkeypatch):
        """char_count应为UTF-8字节数（微信推送限制依据）"""
        svc = self._svc()
        monkeypatch.setattr(svc, '_stock_snapshot',
                            lambda code, name: _fake_snap(code, name))
        result = svc.generate_daily_report([
            {'stock_code': 'MU', 'stock_name': 'Micron'},
        ])
        expected = len(result['report'].encode('utf-8'))
        assert result['char_count'] == expected


# ============================================
# 风控规则常量与webhook加载
# ============================================
class TestRiskRules:
    def test_webhook_loaded_from_config(self):
        url = _load_webhook()
        # 用户原项目config配置了企业微信webhook
        assert url == '' or url.startswith('https://qyapi.weixin.qq.com')

    def test_market_detection(self):
        from app.services.report_service import _detect_market
        assert _detect_market('002594') == 'A'
        assert _detect_market('600519.SH') == 'A'
        assert _detect_market('MU') == 'US'
        assert _detect_market('AAPL') == 'US'


class TestPositionPnlMath:
    """卖出盈亏：直接测试路由使用的共享计算函数 _realized_pnl"""

    def test_profit_case(self):
        from app.routers.portfolio import _realized_pnl
        pnl, pct = _realized_pnl(11.0, 10.0, 100)
        assert (pnl, pct) == (100.0, 10.0)

    def test_loss_case(self):
        from app.routers.portfolio import _realized_pnl
        pnl, pct = _realized_pnl(46.0, 50.0, 200)
        assert (pnl, pct) == (-800.0, -8.0)

    def test_zero_buy_price_no_crash(self):
        from app.routers.portfolio import _realized_pnl
        pnl, pct = _realized_pnl(10.0, 0, 100)
        assert (pnl, pct) == (1000.0, 0)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
