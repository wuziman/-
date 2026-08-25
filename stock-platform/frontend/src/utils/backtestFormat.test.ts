import { describe, expect, it } from 'vitest';
import { colors } from '../theme/tokens';
import { METRIC_LABEL, STRATEGY_COLORS, fmtParams, periodLabel } from './backtestFormat';

describe('periodLabel 回测周期标签', () => {
  it('映射已知周期', () => {
    expect(periodLabel('1y')).toBe('近1年');
    expect(periodLabel('3y')).toBe('近3年');
    expect(periodLabel('5y')).toBe('近5年');
  });

  it('未知/空周期兜底为近1年（与后端默认口径一致）', () => {
    expect(periodLabel(undefined)).toBe('近1年');
    expect(periodLabel('')).toBe('近1年');
  });
});

describe('fmtParams 参数组合展示', () => {
  it('键值对拼接', () => {
    expect(fmtParams({ window: 20, k: 2 })).toBe('window=20, k=2');
  });

  it('空参数返回空串', () => {
    expect(fmtParams({})).toBe('');
  });
});

describe('METRIC_LABEL / STRATEGY_COLORS', () => {
  it('指标中文名齐全', () => {
    expect(METRIC_LABEL.sharpe).toBe('夏普比率');
    expect(METRIC_LABEL.max_drawdown).toBe('最大回撤%');
  });

  it('四策略各有着色且互不重复', () => {
    const cs = Object.values(STRATEGY_COLORS);
    expect(new Set(cs).size).toBe(cs.length);
    expect(STRATEGY_COLORS.linear).toBe(colors.primary);
  });
});
