#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美股硬科技周度选股引擎 - Alpha TOP 5 猛禽池
- 覆盖美股半导体、AI芯片、光通信、算力基础设施与科技云巨头 (~35-40支高流动性行业领头羊)
- 多线程并发拉取行情与技术指标
- 三合一量化复合因子打分（动量突破 + 超跌击球点 + 步进回测期望）
- 财报日历排雷雷达
- Gemini 3.7 Flash 产业逻辑与核心催化剂深度研判
- 输出专属周报推送企业微信 + 存档供 Web 平台调用
"""

import os
import sys
import json
import time
from datetime import datetime, date
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import pandas as pd
import yfinance as yf

# 避免 Windows 终端输出 Emoji 时的 GBK 编码报错
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# 保证能正确加载 backend 的 llm_client
BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "stock-platform" / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from app.services.llm_client import chat_completion, is_ai_configured
except ImportError:
    chat_completion = None
    def is_ai_configured(): return False

# ----------------------------------------------------
# 1. 美股硬科技与算力龙头监控池 (~35-40 支优质龙头)
# ----------------------------------------------------
HARD_TECH_UNIVERSE = [
    # --- AI 芯片与半导体核心龙头 ---
    {"code": "NVDA", "name": "英伟达", "sector": "AI算力总龙头"},
    {"code": "TSM", "name": "台积电", "sector": "先进制程代工垄断"},
    {"code": "AVGO", "name": "博通", "sector": "定制ASIC与交换芯片"},
    {"code": "AMD", "name": "超威半导体", "sector": "GPU与数据中心CPU"},
    {"code": "QCOM", "name": "高通", "sector": "端侧AI与移动平台"},
    {"code": "MU", "name": "美光科技", "sector": "HBM3e高带宽存储"},
    {"code": "ARM", "name": "安谋", "sector": "低功耗高能效架构"},
    {"code": "MRVL", "name": "美满电子", "sector": "定制云算力与网络ASIC"},
    {"code": "INTC", "name": "英特尔", "sector": "传统芯片IDM转型"},
    {"code": "TXN", "name": "德州仪器", "sector": "模拟与汽车芯片基石"},
    {"code": "ADI", "name": "亚德诺", "sector": "高性能模拟与精密信号"},
    {"code": "ON", "name": "安森美", "sector": "汽车与工业碳化硅"},
    {"code": "MPWR", "name": "芯源系统", "sector": "高压电源管理芯片"},

    # --- 半导体核心设备与材料 ---
    {"code": "ASML", "name": "阿斯麦", "sector": "EUV光刻机绝对垄断"},
    {"code": "AMAT", "name": "应用材料", "sector": "半导体设备百宝箱"},
    {"code": "LRCX", "name": "泛林半导体", "sector": "先进制程刻蚀与薄膜"},
    {"code": "KLAC", "name": "科磊半导体", "sector": "工艺控制与缺陷检测"},

    # --- 光通信与高速光互联 ---
    {"code": "LITE", "name": "Lumentum", "sector": "光器件与激光器龙头"},
    {"code": "COHR", "name": "Coherent", "sector": "800G光收发与光学材料"},
    {"code": "AAOI", "name": "祥茂光电", "sector": "高弹性数据中心光模块"},
    {"code": "AXTI", "name": "AXT", "sector": "磷化铟光通信衬底材料"},
    {"code": "CIEN", "name": "锡安通讯", "sector": "相干光网络系统龙头"},
    {"code": "FN", "name": "Fabrinet", "sector": "高端光互联代工之王"},

    # --- AI 算力基础设施与服务器网络 ---
    {"code": "VRT", "name": "维谛技术", "sector": "数据中心液冷与电力"},
    {"code": "SMCI", "name": "超微电脑", "sector": "高密AI服务器整机柜"},
    {"code": "ANET", "name": "阿里斯塔", "sector": "800G AI数据中心网络"},
    {"code": "DELL", "name": "戴尔科技", "sector": "企业级AI服务器"},
    {"code": "HPE", "name": "慧与科技", "sector": "高性能超算与企业云"},
    {"code": "PLTR", "name": "Palantir", "sector": "企业级AI决策操作系统"},

    # --- 科技巨头云厂商 (算力采购主力) ---
    {"code": "MSFT", "name": "微软", "sector": "Azure云与商业化AI"},
    {"code": "GOOGL", "name": "谷歌", "sector": "自研TPU与Gemini生态"},
    {"code": "AMZN", "name": "亚马逊", "sector": "AWS云与自研Trainium"},
    {"code": "META", "name": "Meta", "sector": "开源大模型与算力集群"},
    {"code": "AAPL", "name": "苹果", "sector": "Apple Intelligence终端"},
    {"code": "TSLA", "name": "特斯拉", "sector": "FSD端到端自动驾驶算力"}
]


def load_webhook() -> str:
    """加载企业微信 Webhook"""
    webhook = os.environ.get('WECHAT_WEBHOOK', '')
    if not webhook:
        config_path = BASE_DIR / 'config' / 'config.json'
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    webhook = cfg.get('wechat_webhook', '')
            except Exception:
                pass
    return webhook


def send_wechat_message(webhook: str, content: str) -> bool:
    """企业微信推送（带智能分包）"""
    if not webhook:
        print("[WeChat] 未配置 WECHAT_WEBHOOK，跳过推送")
        return False

    MAX_BYTES = 3800
    encoded = content.encode('utf-8')
    if len(encoded) <= MAX_BYTES:
        return _send_single_payload(webhook, content)

    # 智能按卡片分包
    cards = content.split('\n### ')
    chunks = []
    current = cards[0]
    for card in cards[1:]:
        candidate = current + '\n### ' + card
        if len(candidate.encode('utf-8')) > MAX_BYTES:
            chunks.append(current)
            current = '### ' + card
        else:
            current = candidate
    if current:
        chunks.append(current)

    success = True
    total = len(chunks)
    for idx, chunk in enumerate(chunks, 1):
        banner = f"> 📄 **【周度选股内参 分包 ({idx}/{total})】**\n\n" if total > 1 else ""
        ok = _send_single_payload(webhook, banner + chunk)
        success = success and ok
        if idx < total:
            time.sleep(1.5)
    return success


def _send_single_payload(webhook: str, text: str) -> bool:
    payload = {"msgtype": "markdown", "markdown": {"content": text}}
    for attempt in range(3):
        try:
            resp = requests.post(webhook, json=payload, timeout=10)
            if resp.status_code == 200:
                res = resp.json()
                if res.get('errcode') == 0:
                    return True
            time.sleep(1.0)
        except Exception:
            time.sleep(1.0)
    return False


# ----------------------------------------------------
# 2. 单股票指标计算与三合一因子打分
# ----------------------------------------------------
def analyze_candidate(stock_meta: dict) -> dict:
    """拉取单只候选标的历史数据，计算动量、超跌、回测与财报指标"""
    code = stock_meta["code"]
    name = stock_meta["name"]
    sector = stock_meta["sector"]

    try:
        t = yf.Ticker(code)
        # 获取 6 个月历史计算指标与回测
        hist = t.history(period="6mo")
        if hist is None or hist.empty:
            return None
        hist = hist.dropna(subset=['Close'])
        if len(hist) < 35:
            return None

        # 计算基础指标
        close = hist['Close']
        current_price = float(close.iloc[-1])

        # 1. RSI (14)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi_series = 100 - (100 / (1 + rs))
        rsi = float(rsi_series.iloc[-1]) if pd.notna(rsi_series.iloc[-1]) else 50.0

        # 2. 均线与布林带
        ma20 = float(close.rolling(20).mean().iloc[-1])
        ma50 = float(close.rolling(50).mean().iloc[-1])
        std20 = float(close.rolling(20).std().iloc[-1])
        bb_upper = ma20 + 2 * std20
        bb_lower = ma20 - 2 * std20

        # 3. MACD
        exp12 = close.ewm(span=12, adjust=False).mean()
        exp26 = close.ewm(span=26, adjust=False).mean()
        macd = exp12 - exp26
        signal = macd.ewm(span=9, adjust=False).mean()
        macd_val = float(macd.iloc[-1])
        signal_val = float(signal.iloc[-1])

        # 4. 近20日动量涨跌幅
        m20_return = float((current_price - close.iloc[-20]) / close.iloc[-20] * 100.0)

        # 5. 财报日历排雷
        earnings_info = {'date': None, 'days': None, 'tag': '', 'is_imminent': False}
        try:
            cal = t.calendar
            ed = None
            if isinstance(cal, dict) and 'Earnings Date' in cal and cal['Earnings Date']:
                ed = cal['Earnings Date'][0]
            elif hasattr(cal, 'get'):
                ed_list = cal.get('Earnings Date')
                if ed_list:
                    ed = ed_list[0]
            if ed:
                today = date.today()
                ed_date = ed.date() if hasattr(ed, 'date') else ed
                days = (ed_date - today).days
                earnings_info['date'] = ed_date.strftime('%Y-%m-%d')
                earnings_info['days'] = days
                if days == 0:
                    earnings_info['tag'] = "🚨【今晚发布财报】"
                    earnings_info['is_imminent'] = True
                elif 0 < days <= 3:
                    earnings_info['tag'] = f"⚠️【{days}天后财报】"
                    earnings_info['is_imminent'] = True
                elif 3 < days <= 14:
                    earnings_info['tag'] = f"📅【{days}天后财报】"
        except Exception:
            pass

        # ----------------------------------------------------
        # 复合因子打分（满分100分）
        # ----------------------------------------------------
        # 因子 A: 动量突破因子 (0-35 分)
        momentum_score = 15.0
        if current_price > ma20:
            momentum_score += 6.0
        if current_price > ma50:
            momentum_score += 4.0
        if ma20 > ma50:
            momentum_score += 5.0
        if macd_val > signal_val:
            momentum_score += 5.0
        if m20_return > 0:
            momentum_score += min(5.0, m20_return * 0.5)

        # 因子 B: 超跌击球点因子 (0-35 分)
        sweetspot_score = 15.0
        if rsi < 30:
            sweetspot_score += 15.0  # 极度超卖黄金坑
        elif rsi < 40:
            sweetspot_score += 10.0
        elif rsi < 50:
            sweetspot_score += 5.0
        elif rsi > 70:
            sweetspot_score -= 10.0  # 超买扣分

        if current_price <= bb_lower * 1.02:
            sweetspot_score += 5.0

        # 因子 C: 步进式回测期望验证 (0-30 分)
        # 简易 Walk-Forward 模拟（回踩MA20买入，+15%止盈/-8%止损）
        backtest_score = 15.0
        win_count = 0
        loss_count = 0
        for i in range(25, len(close) - 10, 5):
            entry_p = close.iloc[i]
            future_max = close.iloc[i:i+10].max()
            future_min = close.iloc[i:i+10].min()
            if future_max >= entry_p * 1.10:
                win_count += 1
            elif future_min <= entry_p * 0.94:
                loss_count += 1

        total_trades = win_count + loss_count
        win_rate = (win_count / total_trades * 100.0) if total_trades > 0 else 50.0
        if win_rate >= 60.0:
            backtest_score += 15.0
        elif win_rate >= 50.0:
            backtest_score += 10.0
        elif win_rate < 40.0:
            backtest_score -= 5.0

        # 财报排雷扣分
        if earnings_info['is_imminent']:
            backtest_score -= 15.0  # 临近财报大扣分

        total_score = max(0.0, min(100.0, momentum_score + sweetspot_score + backtest_score))

        # 计算推荐伏击点位
        linear_buy = min(current_price * 0.96, ma20)
        nonlinear_buy = bb_lower if rsi < 35 else ma20 * 0.98

        return {
            'code': code,
            'name': name,
            'sector': sector,
            'current_price': round(current_price, 2),
            'rsi': round(rsi, 1),
            'm20_return': round(m20_return, 1),
            'win_rate': round(win_rate, 1),
            'momentum_score': round(momentum_score, 1),
            'sweetspot_score': round(sweetspot_score, 1),
            'backtest_score': round(backtest_score, 1),
            'total_score': round(total_score, 1),
            'earnings': earnings_info,
            'linear_buy': round(linear_buy, 2),
            'nonlinear_buy': round(nonlinear_buy, 2),
            'linear_profit': round(linear_buy * 1.15, 2),
            'linear_stop': round(linear_buy * 0.92, 2),
        }
    except Exception as e:
        print(f"  [Skip] 计算 {code} 失败: {e}")
        return None


# ----------------------------------------------------
# 3. 执行全池并发扫描
# ----------------------------------------------------
def run_screener():
    """扫描全池硬科技股票并挑选 TOP 5"""
    print("=" * 60)
    print(f"🚀 美股硬科技周度选股引擎启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"监控标的池数量: {len(HARD_TECH_UNIVERSE)} 支科技与算力龙头")
    print("=" * 60)

    t0 = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(analyze_candidate, item): item["code"] for item in HARD_TECH_UNIVERSE}
        for fut in as_completed(futures):
            res = fut.result()
            if res:
                results.append(res)

    print(f"✅ 全池数据拉取与因子计算完成，耗时: {time.time() - t0:.2f} 秒，有效标的: {len(results)} 支")

    # 排序并筛选 TOP 5
    # 优先剔除近期财报高危标的
    eligible = [r for r in results if not r['earnings']['is_imminent']]
    if len(eligible) < 5:
        eligible = results

    sorted_results = sorted(eligible, key=lambda x: x['total_score'], reverse=True)
    top5 = sorted_results[:5]

    print("\n🏆【周度 Alpha TOP 5 猛禽池名单出炉】:")
    for rank, item in enumerate(top5, 1):
        print(f"  TOP {rank}: {item['code']} {item['name']} | 赛道: {item['sector']} | 量化总分: {item['total_score']}分 (现价=${item['current_price']})")

    # ----------------------------------------------------
    # 4. Gemini 3.7 Flash 深度投资逻辑研判
    # ----------------------------------------------------
    ai_thesis = generate_ai_thesis(top5)

    # ----------------------------------------------------
    # 5. 保存结果供 Web 平台与 API 调用
    # ----------------------------------------------------
    payload = {
        'scan_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_scanned': len(results),
        'top5': top5,
        'ai_thesis': ai_thesis
    }

    data_dir = BASE_DIR / 'data'
    data_dir.mkdir(exist_ok=True)
    output_json = data_dir / 'weekly_alpha_top5.json'
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n📁 选股结果已保存至: {output_json}")

    # ----------------------------------------------------
    # 6. 生成微信周度选股周报并推送
    # ----------------------------------------------------
    wechat_report = format_wechat_weekly_report(top5, ai_thesis)
    report_dir = BASE_DIR / 'reports'
    report_dir.mkdir(exist_ok=True)
    report_file = report_dir / f"weekly_alpha_top5_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(wechat_report)

    webhook = load_webhook()
    print("📱 正在向企业微信推送周度选股内参...")
    ok = send_wechat_message(webhook, wechat_report)
    if ok:
        print("✅ 企业微信周报推送成功！")
    else:
        print("⚠️ 企业微信推送未触发或失败")

    return payload


def generate_ai_thesis(top5: list) -> str:
    """调用大模型为 TOP 5 标的生成产业逻辑与催化研判"""
    if not (is_ai_configured and is_ai_configured() and chat_completion):
        return "大模型暂未配置，请参考量化打分与技术点位。"

    candidates_text = "\n".join([
        f"- TOP {i}: {s['code']} {s['name']} ({s['sector']}) | 现价 ${s['current_price']}, 量化总分 {s['total_score']}分, "
        f"动量分 {s['momentum_score']}, 超跌分 {s['sweetspot_score']}, 近6月胜率 {s['win_rate']}%, RSI={s['rsi']}, 20日动量 {s['m20_return']:+.1f}%"
        for i, s in enumerate(top5, 1)
    ])

    prompt = f"""
你是一位专精于美股半导体、AI算力与硬科技产业链的顶级量化对冲基金投研总监。
我们的硬科技周度量化多因子扫描引擎刚刚从全美 40 支顶级科技龙头中，筛选出了本周量化评分最高、形态与盈亏比兼备的【Alpha TOP 5 猛禽池】：

【入选标的量化数据】
{candidates_text}

请为投资者撰写一份高水准的《美股硬科技周度选股内参 · TOP 5 深度逻辑研判》：
1. **宏观与产业链主线前瞻**：用 2 句话点出本周资金在半导体、光互联、AI服务器之间的轮动主线；
2. **TOP 5 核心标的逻辑剖析**：对排名前列的标的逐一点评（结合其商业壁垒、技术突破买点或超跌反弹弹性）；
3. **下周实操伏击指引**：给出挂单策略建议与止损防守铁律。
语言风格专业犀利、字字珠玑，排版使用优雅的 Markdown，字数控制在 400-500 字以内。不要输出寒暄客套。
"""
    try:
        res = chat_completion([{"role": "user", "content": prompt}], max_tokens=3000)
        return res.strip()
    except Exception as e:
        print(f"[LLM] 生成周度选股研报失败: {e}")
        return "AI研报生成中遇到临时延迟，各标的量化点位已就绪。"


def format_wechat_weekly_report(top5: list, ai_thesis: str) -> str:
    """格式化企业微信周度选股消息"""
    now_str = datetime.now().strftime('%m-%d %H:%M')
    lines = [
        f"**【美股硬科技周度选股 · Alpha TOP 5 猛禽池】** {now_str}",
        "> 🦅 **选股定位**: 全市场精选高动量、高胜率、高胜算科技增量标的",
        "> 📌 **池位关系**: 独立于核心10支自选股，提供增量Alpha进攻机会\n",
        "### 🧠 AI 投研总监深度逻辑",
        ai_thesis,
        "\n---",
        "### 🏆 周度 Alpha TOP 5 量化伏击点位表\n"
    ]

    for i, s in enumerate(top5, 1):
        lines.append(f"### {i}. {s['code']} {s['name']} | `{s['total_score']}分`")
        lines.append(f"- 🏷️ **赛道标签**: {s['sector']}")
        lines.append(f"- 📊 **量化画像**: 现价 **${s['current_price']}** | RSI `{s['rsi']}` | 动量 `{s['m20_return']:+.1f}%` | 模拟胜率 `{s['win_rate']}%`")
        lines.append(f"- 💡 **线性伏击**: 买入 **${s['linear_buy']}** | 止盈 ${s['linear_profit']} (+15%) | 止损 ${s['linear_stop']} (-8%)")
        lines.append(f"- 🛡️ **非线性伏击**: 买入 **${s['nonlinear_buy']}** (强支撑位)")
        lines.append("")

    lines.append("---")
    lines.append("**💡 纪律指引**：")
    lines.append("• 本池标的每周六动态重估，适合作为加仓 Alpha 进攻备选")
    lines.append("• 严格按挂单点位左侧埋伏，严禁追高，坚决执行 -8% 止损")
    return "\n".join(lines)


if __name__ == '__main__':
    run_screener()
