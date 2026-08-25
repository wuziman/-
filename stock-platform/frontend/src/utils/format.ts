// 通用格式化函数（纯函数，便于单测）
import { colors } from '../theme/tokens';

// 三策略点位：价格两位小数；后端指标不足时字段为 null，显示占位符
export const fmtPx = (v: number | null) => (v == null ? '--' : `$${v.toFixed(2)}`);

// 距离百分比：带正负号
export const fmtDist = (v: number | null) => (v == null ? '--' : `${v > 0 ? '+' : ''}${v.toFixed(2)}%`);

// 涨跌三色：正绿/负红/零与无值灰（DESIGN.md 盈亏语义约定）
export const pctColor = (v: number) => (v > 0 ? colors.profit : v < 0 ? colors.loss : colors.textSecondary);
