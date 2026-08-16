"""
仓位管理系统
根据评分和策略动态调整仓位
"""

import json
from datetime import datetime


class PositionManager:
    """仓位管理器"""

    def __init__(self, total_capital=15000):
        self.total_capital = total_capital
        self.cash = total_capital
        self.positions = {}
        self.reserve_ratio = 0.2  # 保留20%现金

    def calculate_position_size(self, stock_score, strategy_type="both"):
        """
        根据评分计算仓位大小

        参数：
            stock_score: 综合评分（0-10分）
            strategy_type: "linear"（线性）/ "nonlinear"（非线性）/ "both"（两者都用）

        返回：
            建议仓位金额
        """
        # 基础仓位比例（根据评分）
        if stock_score >= 8.0:
            base_ratio = 0.4  # 40%
        elif stock_score >= 6.5:
            base_ratio = 0.3  # 30%
        elif stock_score >= 5.0:
            base_ratio = 0.2  # 20%
        elif stock_score >= 3.5:
            base_ratio = 0.1  # 10%
        else:
            base_ratio = 0  # 不买入

        # 根据策略类型调整
        if strategy_type == "nonlinear":
            # 非线性策略：仓位可以更大（因为胜率高）
            adjusted_ratio = base_ratio * 1.2
        elif strategy_type == "linear":
            # 线性策略：仓位适中
            adjusted_ratio = base_ratio
        else:
            # 两者都用：取平均
            adjusted_ratio = base_ratio

        # 计算金额
        position_size = self.total_capital * adjusted_ratio

        # 确保不超过可用现金
        available_cash = self.cash - (self.total_capital * self.reserve_ratio)
        position_size = min(position_size, available_cash)

        return position_size

    def calculate_stop_loss(self, buy_price, strategy_type="linear"):
        """
        计算止损价

        参数：
            buy_price: 买入价
            strategy_type: 策略类型

        返回：
            止损价
        """
        if strategy_type == "nonlinear":
            # 非线性策略：止损-8%
            return buy_price * 0.92
        else:
            # 线性策略：止损-8%
            return buy_price * 0.92

    def calculate_take_profit(self, buy_price, strategy_type="linear"):
        """
        计算止盈价

        参数：
            buy_price: 买入价
            strategy_type: 策略类型

        返回：
            止盈价
        """
        if strategy_type == "nonlinear":
            # 非线性策略：止盈+46%
            return buy_price * 1.46
        else:
            # 线性策略：止盈+15%
            return buy_price * 1.15

    def should_add_position(self, stock_code, current_price, buy_price, strategy_type="linear"):
        """
        判断是否应该补仓

        参数：
            stock_code: 股票代码
            current_price: 当前价
            buy_price: 买入价
            strategy_type: 策略类型

        返回：
            (是否补仓, 补仓金额)
        """
        if stock_code not in self.positions:
            return False, 0

        position = self.positions[stock_code]
        current_cost = position['avg_price']
        current_shares = position['shares']

        # 计算下跌幅度
        drop_percent = (current_cost - current_price) / current_cost * 100

        # 补仓规则
        if strategy_type == "nonlinear":
            # 非线性策略：下跌5%补仓25%，下跌10%补仓25%，下跌15%补仓25%
            if drop_percent >= 15:
                add_ratio = 0.25
            elif drop_percent >= 10:
                add_ratio = 0.25
            elif drop_percent >= 5:
                add_ratio = 0.25
            else:
                return False, 0
        else:
            # 线性策略：下跌5%补仓20%，下跌10%补仓20%，下跌15%补仓20%
            if drop_percent >= 15:
                add_ratio = 0.20
            elif drop_percent >= 10:
                add_ratio = 0.20
            elif drop_percent >= 5:
                add_ratio = 0.20
            else:
                return False, 0

        # 计算补仓金额
        original_position = self.total_capital * 0.3  # 假设原始仓位30%
        add_amount = original_position * add_ratio

        # 确保不超过可用现金
        available_cash = self.cash - (self.total_capital * self.reserve_ratio)
        add_amount = min(add_amount, available_cash)

        if add_amount > 0:
            return True, add_amount
        else:
            return False, 0

    def buy(self, stock_code, price, amount, strategy_type="linear"):
        """
        买入股票
        """
        shares = int(amount / price)
        cost = shares * price

        if cost > self.cash:
            print(f"现金不足，需要${cost:.2f}，可用${self.cash:.2f}")
            return False

        self.cash -= cost

        if stock_code in self.positions:
            # 加仓
            position = self.positions[stock_code]
            total_shares = position['shares'] + shares
            total_cost = position['cost'] + cost
            avg_price = total_cost / total_shares

            self.positions[stock_code] = {
                'shares': total_shares,
                'avg_price': avg_price,
                'cost': total_cost,
                'strategy': strategy_type
            }
            print(f"加仓 {stock_code}: +{shares}股 @ ${price}，总持仓{total_shares}股，平均成本${avg_price:.2f}")
        else:
            # 新建仓位
            self.positions[stock_code] = {
                'shares': shares,
                'avg_price': price,
                'cost': cost,
                'strategy': strategy_type
            }
            print(f"买入 {stock_code}: {shares}股 @ ${price}，花费${cost:.2f}")

        return True

    def sell(self, stock_code, price):
        """
        卖出股票
        """
        if stock_code not in self.positions:
            print(f"没有持仓 {stock_code}")
            return False

        position = self.positions[stock_code]
        revenue = position['shares'] * price
        profit = revenue - position['cost']
        profit_percent = profit / position['cost'] * 100

        self.cash += revenue
        del self.positions[stock_code]

        print(f"卖出 {stock_code}: {position['shares']}股 @ ${price}，盈亏${profit:.2f} ({profit_percent:.2f}%)")
        return True

    def check_stop_loss(self, stock_code, current_price):
        """
        检查止损
        """
        if stock_code not in self.positions:
            return False

        position = self.positions[stock_code]
        stop_loss = self.calculate_stop_loss(position['avg_price'], position['strategy'])

        if current_price <= stop_loss:
            print(f"{stock_code} 触发止损，当前价${current_price} <= 止损价${stop_loss:.2f}")
            self.sell(stock_code, current_price)
            return True

        return False

    def check_take_profit(self, stock_code, current_price):
        """
        检查止盈
        """
        if stock_code not in self.positions:
            return False

        position = self.positions[stock_code]
        take_profit = self.calculate_take_profit(position['avg_price'], position['strategy'])

        if current_price >= take_profit:
            print(f"{stock_code} 触发止盈，当前价${current_price} >= 止盈价${take_profit:.2f}")
            self.sell(stock_code, current_price)
            return True

        return False

    def get_position_summary(self):
        """
        获取持仓 summary
        """
        total_value = self.cash

        print(f"\n{'='*60}")
        print("持仓 summary")
        print(f"{'='*60}")
        print(f"现金: ${self.cash:.2f} ({self.cash/self.total_capital*100:.1f}%)")

        for stock_code, pos in self.positions.items():
            total_value += pos['cost']
            print(f"{stock_code}: {pos['shares']}股，平均成本${pos['avg_price']:.2f}，总成本${pos['cost']:.2f}，策略: {pos['strategy']}")

        print(f"{'='*60}")
        print(f"总资产: ${total_value:.2f}")
        print(f"现金比例: {self.cash/total_value*100:.1f}%")
        print(f"持仓比例: {(total_value-self.cash)/total_value*100:.1f}%")
        print(f"{'='*60}")

        return total_value


def generate_position_plan(results, total_capital=15000):
    """
    生成仓位配置建议

    参数：
        results: 股票分析结果列表
        total_capital: 总资金

    返回：
        仓位配置建议
    """
    print(f"\n{'='*60}")
    print("仓位配置建议")
    print(f"总资金: ${total_capital:,.2f}")
    print(f"{'='*60}")

    # 按评分排序
    sorted_results = sorted(results, key=lambda x: x['total_score'], reverse=True)

    # 选择最好的1-2只股票
    selected_stocks = []
    for result in sorted_results[:2]:  # 只选前2只
        if result['total_score'] >= 5.0:  # 评分>=5分才考虑
            selected_stocks.append(result)

    if not selected_stocks:
        print("没有符合条件的股票，建议持有现金")
        return []

    # 计算仓位
    manager = PositionManager(total_capital)
    position_plan = []

    for stock in selected_stocks:
        stock_code = stock['stock_code']
        stock_name = stock['stock_name']
        total_score = stock['total_score']

        # 计算建议仓位
        position_size = manager.calculate_position_size(total_score, "both")

        # 计算买入股数
        linear_buy = stock['linear']['buy']
        nonlinear_buy = stock['nonlinear']['buy']

        # 使用非线性策略的买入价（因为胜率更高）
        buy_price = nonlinear_buy
        shares = int(position_size / buy_price)
        actual_cost = shares * buy_price

        # 计算止损止盈
        stop_loss = manager.calculate_stop_loss(buy_price, "nonlinear")
        take_profit = manager.calculate_take_profit(buy_price, "nonlinear")

        plan = {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'total_score': total_score,
            'position_size': position_size,
            'buy_price': buy_price,
            'shares': shares,
            'actual_cost': actual_cost,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'stop_loss_percent': (buy_price - stop_loss) / buy_price * 100,
            'take_profit_percent': (take_profit - buy_price) / buy_price * 100
        }
        position_plan.append(plan)

        print(f"\n{stock_code} {stock_name} (评分: {total_score:.1f}分)")
        print(f"  建议仓位: ${position_size:,.2f} ({position_size/total_capital*100:.1f}%)")
        print(f"  买入价: ${buy_price:.2f}")
        print(f"  买入股数: {shares}股")
        print(f"  实际成本: ${actual_cost:,.2f}")
        print(f"  止损价: ${stop_loss:.2f} (-{plan['stop_loss_percent']:.1f}%)")
        print(f"  止盈价: ${take_profit:.2f} (+{plan['take_profit_percent']:.1f}%)")

    # 计算总投入
    total_invested = sum(p['actual_cost'] for p in position_plan)
    cash_remaining = total_capital - total_invested

    print(f"\n{'='*60}")
    print("配置 summary")
    print(f"{'='*60}")
    print(f"总资金: ${total_capital:,.2f}")
    print(f"总投入: ${total_invested:,.2f} ({total_invested/total_capital*100:.1f}%)")
    print(f"剩余现金: ${cash_remaining:,.2f} ({cash_remaining/total_capital*100:.1f}%)")
    print(f"{'='*60}")

    return position_plan


def generate_add_position_plan(stock_code, current_price, avg_cost, strategy_type="nonlinear"):
    """
    生成补仓计划

    参数：
        stock_code: 股票代码
        current_price: 当前价
        avg_cost: 平均成本
        strategy_type: 策略类型

    返回：
        补仓建议
    """
    print(f"\n{'='*60}")
    print(f"{stock_code} 补仓计划")
    print(f"{'='*60}")

    # 计算下跌幅度
    drop_percent = (avg_cost - current_price) / avg_cost * 100

    print(f"平均成本: ${avg_cost:.2f}")
    print(f"当前价: ${current_price:.2f}")
    print(f"下跌幅度: {drop_percent:.2f}%")

    # 补仓规则
    if strategy_type == "nonlinear":
        rules = [
            (5, 0.25, "补仓25%"),
            (10, 0.25, "补仓25%"),
            (15, 0.25, "补仓25%")
        ]
    else:
        rules = [
            (5, 0.20, "补仓20%"),
            (10, 0.20, "补仓20%"),
            (15, 0.20, "补仓20%")
        ]

    print(f"\n补仓规则:")
    for drop, ratio, desc in rules:
        print(f"  下跌{drop}%: {desc}")

    # 判断当前应该补多少
    add_ratio = 0
    for drop, ratio, desc in rules:
        if drop_percent >= drop:
            add_ratio = ratio

    if add_ratio > 0:
        # 计算补仓金额（假设原始仓位30%）
        original_position = 15000 * 0.3
        add_amount = original_position * add_ratio
        add_shares = int(add_amount / current_price)

        print(f"\n当前建议:")
        print(f"  补仓比例: {add_ratio*100:.0f}%")
        print(f"  补仓金额: ${add_amount:,.2f}")
        print(f"  补仓股数: {add_shares}股")
        print(f"  补仓后成本: ${(avg_cost * 1000 + current_price * add_shares) / (1000 + add_shares):.2f}")
    else:
        print(f"\n当前不需要补仓（下跌幅度未达到{rules[0][0]}%）")

    return add_ratio


def main():
    """主函数"""
    print("仓位管理系统")
    print("=" * 60)

    # 示例：生成仓位配置
    # 假设我们有以下分析结果
    sample_results = [
        {
            'stock_code': 'MU',
            'stock_name': '美光科技',
            'total_score': 6.1,
            'linear': {'buy': 923.08},
            'nonlinear': {'buy': 890.05}
        },
        {
            'stock_code': 'SOXL',
            'stock_name': '半导体ETF',
            'total_score': 5.9,
            'linear': {'buy': 137.70},
            'nonlinear': {'buy': 133.32}
        },
        {
            'stock_code': 'COHR',
            'stock_name': 'Coherent',
            'total_score': 5.9,
            'linear': {'buy': 309.54},
            'nonlinear': {'buy': 303.75}
        }
    ]

    # 生成仓位配置
    position_plan = generate_position_plan(sample_results, 15000)

    # 示例：生成补仓计划
    print("\n" + "="*60)
    print("补仓计划示例")
    print("="*60)

    # MU补仓计划（假设已经买入，成本$923，当前价$890）
    generate_add_position_plan('MU', 890.05, 923.08, 'nonlinear')


if __name__ == "__main__":
    main()
