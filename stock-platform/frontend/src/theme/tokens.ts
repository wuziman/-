// 全站颜色唯一定义处（设计约定见 frontend/DESIGN.md）。
// 页面与图表一律从这里取色，不要再写裸 hex。
export const colors = {
  // 主色（antd 默认蓝）：品牌标题、链接、图表主序列
  primary: '#1890ff',

  // ===== 盈亏与评级语义（文字/数值着色）=====
  profit: '#3f8600',    // 正收益 / 盈利
  loss: '#cf1322',      // 负收益 / 亏损
  warning: '#faad14',   // 警示 / 中性评级
  success: '#52c41a',   // 成功 / 高评分（≥8）
  error: '#ff4d4f',     // 错误 / 低评分（<4）

  // ===== K线域语义（A股惯例：红涨绿跌，仅K线图，勿与盈亏语义混用）=====
  klineUp: '#ef232a',
  klineDown: '#14b143',

  // ===== 图表系列色 =====
  chartPurple: '#722ed1',     // 非线性策略 / MA50
  chartCyan: '#13c2c2',       // 双均线交叉策略
  chartOrange: '#fa8c16',     // MACD策略
  ma5: '#f5a623',             // MA5均线
  indicatorBlue: '#5470c6',   // 技术指标线（echarts默认蓝）
  chartNeutral: '#8c8c8c',    // 图表基准线（虚线）

  // ===== 中性色 =====
  textSecondary: '#595959',   // 次要文字（白底对比度约7:1，达WCAG AA）
  border: '#f0f0f0',          // 分隔线/描边
  bgLight: '#f5f5f5',         // 浅背景（代码块/表底）
  bgSecondary: '#fafafa',     // 次级背景（日报正文底色）
} as const;
