// echarts按需注册（全量引入约1MB，按需后仅打包用到的图表与组件）
// 新增图表类型或option组件时，必须在这里同步注册，否则运行时静默不渲染
import * as echarts from 'echarts/core';
import {
  BarChart,
  CandlestickChart,
  HeatmapChart,
  LineChart,
  PieChart,
  ScatterChart,
} from 'echarts/charts';
import {
  DataZoomInsideComponent,
  DataZoomSliderComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([
  // 图表系列
  LineChart, BarChart, PieChart, ScatterChart, CandlestickChart, HeatmapChart,
  // option组件
  GridComponent, TooltipComponent, LegendComponent, TitleComponent,
  DataZoomInsideComponent, DataZoomSliderComponent,
  MarkLineComponent, VisualMapComponent,
  // 渲染器
  CanvasRenderer,
]);

export default echarts;
