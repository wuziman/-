import { describe, expect, it } from 'vitest';
import { colors } from '../theme/tokens';
import { fmtDist, fmtPx, pctColor } from './format';

describe('fmtPx 价格格式化', () => {
  it('两位小数带美元符', () => {
    expect(fmtPx(910.43)).toBe('$910.43');
    expect(fmtPx(864.9)).toBe('$864.90');
  });

  it('null 显示占位符（后端指标不足时点位为null）', () => {
    expect(fmtPx(null)).toBe('--');
  });
});

describe('fmtDist 距离格式化', () => {
  it('正数带加号', () => {
    expect(fmtDist(5)).toBe('+5.00%');
  });

  it('负数自带减号', () => {
    expect(fmtDist(-3.2)).toBe('-3.20%');
  });

  it('零不带符号', () => {
    expect(fmtDist(0)).toBe('0.00%');
  });

  it('null 显示占位符', () => {
    expect(fmtDist(null)).toBe('--');
  });
});

describe('pctColor 涨跌三色（DESIGN.md 盈亏语义）', () => {
  it('正→profit绿', () => {
    expect(pctColor(1.5)).toBe(colors.profit);
  });

  it('负→loss红', () => {
    expect(pctColor(-0.1)).toBe(colors.loss);
  });

  it('零→textSecondary灰（零值不得着绿）', () => {
    expect(pctColor(0)).toBe(colors.textSecondary);
  });
});
