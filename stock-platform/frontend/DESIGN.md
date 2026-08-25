# DESIGN.md — 量化平台前端设计系统

本文件描述本前端的设计约定。改 UI 前先读这里；颜色一律从 `src/theme/tokens.ts` 取（`colors.*`），**禁止再写裸 hex**。

## 定位

- **模式**：Operate（工具型操作界面）——可扫读、一致、符合 antd 直觉优先于个性化表达。
- **基座**：antd 5（zh_CN locale）+ React + Vite。不重造组件，只做约定与语义层。

## 颜色（唯一定义处：`src/theme/tokens.ts`）

| Token | 值 | 用途 |
|---|---|---|
| `primary` | `#0958d9` | 品牌标题、链接、图表主序列、antd 主色（取 blue-7：主按钮白字对比度达 AA；勿再回退 #1890ff） |
| `profit` | `#3f8600` | 正收益/盈利（**文字**） |
| `loss` | `#cf1322` | 负收益/亏损（**文字**） |
| `warning` | `#faad14` | 警示、中性评级 |
| `success` | `#52c41a` | 成功、高评分（≥8） |
| `error` | `#ff4d4f` | 错误、低评分（<4） |
| `klineUp` | `#ef232a` | K线**阳线**（红涨） |
| `klineDown` | `#14b143` | K线**阴线**（绿跌） |
| `chartPurple` | `#722ed1` | 非线性策略线、MA50 |
| `chartCyan` | `#13c2c2` | 双均线交叉策略线 |
| `chartOrange` | `#fa8c16` | MACD策略线 |
| `ma5` | `#f5a623` | MA5 均线 |
| `indicatorBlue` | `#5470c6` | 技术指标线（echarts 默认蓝） |
| `chartNeutral` | `#8c8c8c` | 图表基准虚线 |
| `textSecondary` | `#595959` | 次要文字（白底 ≈7:1，达 WCAG AA） |
| `border` | `#f0f0f0` | 分隔线/描边 |
| `bgLight` | `#f5f5f5` | 浅背景（代码块、表底） |
| `bgSecondary` | `#fafafa` | 次级背景（日报正文底） |

### 两条铁律

1. **红涨绿跌是 K 线域语义，不是盈亏文字语义。** K 线图用 `klineUp/klineDown`（#ef232a/#14b143），盈亏数字用 `profit/loss`（#3f8600/#cf1322）。两者不可混用——A股用户对"红=涨"的预期只适用于 K 线与涨跌标签。
2. **灰色文字下限是 `textSecondary`(#595959)。** #8c8c8c/#999 等更浅灰只允许出现在图表元素（线、标记）中，不得用于正文。

## 图表约定

- echarts 一律**按需注册**：新增图表类型/组件必须同步登记到 `src/services/echarts.ts`，否则运行时静默不渲染。
- 图表实例统一用 `ReactEChartsCore` + `echarts={echarts}`（来自 services/echarts）。
- 涨跌着色函数约定：正→`profit`，负→`loss`，零/无→`textSecondary`。
- 评分着色：≥8 `success`，≥6 `primary`，≥4 `warning`，否则 `error`。

## 布局与响应式

- 栅格：统计卡行用 antd `Row gutter={16}`；**每张卡必须带小屏断点**，模式：
  - 4-5 卡行：`<Col xs={12} md={8} lg={原始span}>`
  - 2 卡行：`<Col xs={24} sm={12}>`
- 弹窗：**禁止固定像素宽度**，统一 `width="92%"` + `style={{ maxWidth: <原设计宽度> }}`。
- 表格列多时给 `scroll={{ x: ... }}`，移动端横向滚动优于挤压。

## 可访问性

- 图标按钮必须有 `aria-label`（中文动作名，如"修改持仓"）。
- 文字对比度 ≥4.5:1（AA）；图表数据色不受此限，但图例/轴标签按文字处理。

## 性能

- 路由级 `React.lazy` + `Suspense`（见 `App.tsx`）；新页面照抄该模式。
- 重库（echarts）只在用到的页面 import，经 services/echarts 单点注册。

## 明确不做

- 不引入暗色主题（antd 默认亮色即全站基调）。
- 不自定义 antd theme token，保持默认蓝 `#1890ff` 与默认圆角。
- 不为一次性样式建抽象；两处以上重复且语义相同才提取。
