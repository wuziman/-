import React, { useRef, useState, useEffect } from 'react';
import { Card, Input, Select, Button, Row, Col, Form, InputNumber, DatePicker, Table, Tag, Statistic, Space, message, Descriptions, Divider } from 'antd';
import { SearchOutlined, ExperimentOutlined, AimOutlined, PlayCircleOutlined } from '@ant-design/icons';
import ReactEChartsCore from 'echarts-for-react/lib/core';
import echarts from '../services/echarts';
import { stockApi, backtestApi } from '../services/api';
import { colors } from '../theme/tokens';

const { Search } = Input;
const { Option } = Select;

interface Strategy {
  id: string;
  name: string;
  description: string;
}

interface BacktestResult {
  stock_code: string;
  strategy: string;
  total_return: number;
  annual_return: number;
  max_drawdown: number;
  sharpe_ratio: number;
  win_rate: number;
  trade_count: number;
  initial_capital: number;
  final_value: number;
  equity_curve: Array<{ date: string; value: number }>;
  period: string;
  date_range?: string;   // 自定义起止日期时由后端返回实际窗口
  trades: Array<{
    date: string;
    action: string;
    price: number;
    shares: number;
    profit_pct?: number;
    fee?: number;
  }>;
  total_fees?: number;
  commission_per_trade?: number;
  buy_hold_curve?: Array<{ date: string; value: number }>;
  buy_hold_return?: number;
}

interface CompareRow {
  name: string;
  key: string;
  total_return: number;
  annual_return: number;
  max_drawdown: number;
  sharpe_ratio: number;
  win_rate: number;
  trade_count: number;
  total_fees: number;
  excess_vs_buy_hold: number;
}

interface CompareResult {
  stock_code: string;
  period: string;
  initial_capital: number;
  strategies: Record<string, BacktestResult>;
  buy_hold: {
    total_return: number;
    annual_return: number;
    max_drawdown: number;
    sharpe_ratio: number;
    equity_curve: Array<{ date: string; value: number }>;
  };
  comparison: CompareRow[];
}

// 🎯 参数寻优
interface OptimizeRow {
  params: Record<string, number>;
  total_return: number;
  annual_return: number;
  max_drawdown: number;
  sharpe_ratio: number;
  win_rate: number;
  trade_count: number;
  final_value: number;
}

interface HeatmapData {
  x_name: string;
  y_name: string;
  x_values: number[];
  y_values: number[];
  z: Array<Array<number | null>>;
}

interface OptimizeResult {
  stock_code: string;
  strategy: string;
  metric: string;
  period?: string;             // 回显实际回测口径
  initial_capital?: number;
  best: OptimizeRow;
  results: OptimizeRow[];
  heatmap: HeatmapData;
}

// 🔬 Walk-Forward验证
interface WFSegment {
  step: number;
  train_range: [string, string];
  test_range: [string, string];
  best_params: Record<string, number>;
  is_sharpe: number;
  oos_return: number;
  oos_sharpe: number;
  oos_max_drawdown: number;
  oos_buy_hold_return: number;
  beats_buy_hold: boolean;
}

interface WFResult {
  stock_code: string;
  strategy: string;
  period?: string;             // 回显实际回测口径
  initial_capital?: number;
  train_ratio: number;
  segments: WFSegment[];
  stitched_oos_curve: Array<{ date: string; value: number }>;
  oos_buy_hold_curve: Array<{ date: string; value: number }>;
  summary: {
    avg_oos_return: number;
    avg_oos_sharpe: number;
    win_segments: number;
    total_segments: number;
  };
}

// 各策略折线颜色
const STRATEGY_COLORS: Record<string, string> = {
  linear: colors.primary,
  nonlinear: colors.chartPurple,
  ma_cross: colors.chartCyan,
  macd: colors.chartOrange,
};

// 涨跌着色：正绿负红零灰
const pctColor = (v: number) => (v > 0 ? colors.profit : v < 0 ? colors.loss : colors.textSecondary);

// 参数dict格式化为 "tp=0.15, sl=0.08"
const fmtParams = (p: Record<string, number>) =>
  Object.entries(p || {}).map(([k, v]) => `${k}=${v}`).join(', ');

// 寻优排序指标中文名
const METRIC_LABEL: Record<string, string> = {
  sharpe: '夏普比率',
  total_return: '总收益%',
  annual_return: '年化收益%',
  max_drawdown: '最大回撤%',
  win_rate: '胜率%',
  trade_count: '交易次数',
};

const periodLabel = (p?: string) => (p === '3y' ? '近3年' : p === '5y' ? '近5年' : '近1年');

const Backtest: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [selectedStock, setSelectedStock] = useState<any>(null);
  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareResult, setCompareResult] = useState<CompareResult | null>(null);
  // 🎯 参数寻优
  const [optLoading, setOptLoading] = useState(false);
  const [optStrategy, setOptStrategy] = useState('linear');
  const [optResult, setOptResult] = useState<OptimizeResult | null>(null);
  // 🔬 Walk-Forward验证
  const [wfLoading, setWfLoading] = useState(false);
  const [wfStrategy, setWfStrategy] = useState('linear');
  const [wfSegments, setWfSegments] = useState<number>(2);
  const [wfResult, setWfResult] = useState<WFResult | null>(null);

  // 切股请求序号：切换后丢弃在途的回测/对比/寻优响应，防止旧股票结果重新写入
  const selectSeqRef = useRef(0);

  // 切换股票时清空旧结果，避免不同股票的回测/对比/寻优结果混排一页
  const handleSelectStock = (stock: any) => {
    selectSeqRef.current += 1;
    setSelectedStock(stock);
    setBacktestResult(null);
    setCompareResult(null);
    setOptResult(null);
    setWfResult(null);
  };
  const [form] = Form.useForm();
  const dateRangeWatch = Form.useWatch('date_range', form);   // 自定义时间段优先于周期

  const fetchStrategies = async () => {
    try {
      const response = await backtestApi.getStrategies();
      setStrategies(response.data.strategies);
    } catch {
      console.error('获取策略列表失败');
    }
  };

  useEffect(() => {
    fetchStrategies();
  }, []);

  const handleSearch = async (value: string) => {
    if (!value.trim()) return;

    try {
      const response = await stockApi.search(value);
      setSearchResults(response.data.results);
    } catch {
      message.error('搜索失败');
    }
  };

  const handleRunBacktest = async () => {
    try {
      const values = await form.validateFields();

      if (!selectedStock) {
        message.warning('请先选择股票');
        return;
      }

      setLoading(true);
      const seq = selectSeqRef.current;

      const response = await backtestApi.runBacktest({
        stock_code: selectedStock.code,
        strategy: values.strategy,
        period: values.period,
        start_date: values.date_range?.[0]?.format('YYYY-MM-DD'),
        end_date: values.date_range?.[1]?.format('YYYY-MM-DD'),
        initial_capital: values.initial_capital
      });

      if (seq !== selectSeqRef.current) return; // 等待期间已切股，丢弃过期结果
      setBacktestResult(response.data);
      message.success('回测完成');
    } catch (error: any) {
      if (error.errorFields) {
        return;
      }
      message.error('回测失败');
    } finally {
      setLoading(false);
    }
  };

  // ⚡ 一键对比4策略 + 买入持有基准
  const handleRunCompare = async () => {
    if (!selectedStock) {
      message.warning('请先选择股票');
      return;
    }

    try {
      setCompareLoading(true);
      const seq = selectSeqRef.current;
      const values = form.getFieldsValue();
      const response = await backtestApi.compare({
        stock_code: selectedStock.code,
        period: values.period || '1y',
        initial_capital: values.initial_capital || 100000
      });
      if (seq !== selectSeqRef.current) return; // 等待期间已切股，丢弃过期结果
      setCompareResult(response.data);
      message.success('对比完成');
    } catch {
      message.error('策略对比失败');
    } finally {
      setCompareLoading(false);
    }
  };

  // 🎯 参数网格寻优
  const handleRunOptimize = async () => {
    if (!selectedStock) {
      message.warning('请先选择股票');
      return;
    }

    try {
      setOptLoading(true);
      const seq = selectSeqRef.current;
      const values = form.getFieldsValue();
      const response = await backtestApi.optimize({
        stock_code: selectedStock.code,
        strategy: optStrategy,
        period: values.period || '1y',
        initial_capital: values.initial_capital || 100000
      });
      if (seq !== selectSeqRef.current) return; // 等待期间已切股，丢弃过期结果
      setOptResult(response.data);
      message.success('寻优完成');
    } catch {
      message.error('参数寻优失败');
    } finally {
      setOptLoading(false);
    }
  };

  // 🔬 Walk-Forward滚动验证
  const handleRunWalkForward = async () => {
    if (!selectedStock) {
      message.warning('请先选择股票');
      return;
    }

    try {
      setWfLoading(true);
      const seq = selectSeqRef.current;
      const values = form.getFieldsValue();
      const response = await backtestApi.walkForward({
        stock_code: selectedStock.code,
        strategy: wfStrategy,
        period: '5y',
        initial_capital: values.initial_capital || 100000,
        segments: wfSegments
      });
      if (seq !== selectSeqRef.current) return; // 等待期间已切股，丢弃过期结果
      setWfResult(response.data);
      message.success('Walk-Forward验证完成');
    } catch {
      message.error('Walk-Forward验证失败');
    } finally {
      setWfLoading(false);
    }
  };

  const getEquityCurveOption = () => {
    if (!backtestResult) return {};
    // 使用后端返回的每日总资产曲线（现金+持仓市值）
    const curve = backtestResult.equity_curve;
    if (!curve || curve.length === 0) return {};

    const series: any[] = [{
      name: '总资产',
      type: 'line',
      data: curve.map(d => d.value),
      smooth: true,
      showSymbol: false,
      lineStyle: { width: 2, color: colors.primary },
      areaStyle: {
        opacity: 0.15,
        color: colors.primary
      }
    }];

    // 叠加买入持有基准（灰色虚线）
    if (backtestResult.buy_hold_curve && backtestResult.buy_hold_curve.length > 0) {
      series.push({
        name: '买入持有基准',
        type: 'line',
        data: backtestResult.buy_hold_curve.map(d => d.value),
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2, color: colors.chartNeutral, type: 'dashed' },
        itemStyle: { color: colors.chartNeutral }
      });
    }

    return {
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          const arr = Array.isArray(params) ? params : [params];
          const lines = arr.map((p: any) =>
            `${p.marker}${p.seriesName}: $${Number(p.value).toLocaleString()}`);
          return [arr[0]?.name, ...lines].join('<br/>');
        }
      },
      legend: { top: 0 },
      xAxis: {
        type: 'category',
        data: curve.map(d => d.date)
      },
      yAxis: {
        type: 'value',
        name: '总资产 ($)',
        scale: true
      },
      dataZoom: [
        { type: 'inside' },
        { type: 'slider', height: 20, bottom: 0 }
      ],
      series
    };
  };

  const getCompareChartOption = () => {
    if (!compareResult) return {};
    const strategyList = [
      { key: 'linear', name: '线性' },
      { key: 'nonlinear', name: '非线性' },
      { key: 'ma_cross', name: '双均线交叉' },
      { key: 'macd', name: 'MACD' }
    ];
    // 4策略同日期轴，取第一个有数据的作为x轴
    const first = strategyList
      .map(s => compareResult.strategies[s.key])
      .find(r => r?.equity_curve && r.equity_curve.length > 0);
    if (!first) return {};
    const dates = first.equity_curve.map(d => d.date);

    const series: any[] = strategyList.map(s => ({
      name: s.name,
      type: 'line',
      data: compareResult.strategies[s.key]?.equity_curve.map(d => d.value) ?? [],
      smooth: true,
      showSymbol: false,
      lineStyle: { width: 2, color: STRATEGY_COLORS[s.key] },
      itemStyle: { color: STRATEGY_COLORS[s.key] }
    }));

    // 买入持有基准：灰色虚线
    series.push({
      name: '买入持有',
      type: 'line',
      data: compareResult.buy_hold.equity_curve.map(d => d.value),
      smooth: true,
      showSymbol: false,
      lineStyle: { width: 2, color: colors.chartNeutral, type: 'dashed' },
      itemStyle: { color: colors.chartNeutral }
    });

    return {
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          const arr = Array.isArray(params) ? params : [params];
          const lines = arr.map((p: any) =>
            `${p.marker}${p.seriesName}: $${Number(p.value).toLocaleString()}`);
          return [arr[0]?.name, ...lines].join('<br/>');
        }
      },
      legend: { top: 0 },
      grid: { top: 40, left: 70, right: 20, bottom: 50 },
      xAxis: {
        type: 'category',
        data: dates
      },
      yAxis: {
        type: 'value',
        name: '总资产 ($)',
        scale: true
      },
      dataZoom: [
        { type: 'inside' },
        { type: 'slider', height: 20, bottom: 0 }
      ],
      series
    };
  };

  // 🎯 寻优热力图：x/y=两维参数，visualMap颜色映射metric值
  const getOptimizeHeatmapOption = () => {
    if (!optResult?.heatmap) return {};
    const hm = optResult.heatmap;
    const data: Array<[number, number, number]> = [];
    hm.z.forEach((row, yi) =>
      row.forEach((v, xi) => {
        if (v !== null && v !== undefined) data.push([xi, yi, v]);
      })
    );
    if (data.length === 0) return {};
    const vals = data.map(d => d[2]);
    const metricName = METRIC_LABEL[optResult.metric] || optResult.metric;
    return {
      tooltip: {
        position: 'top',
        formatter: (p: any) =>
          `${hm.x_name}=${hm.x_values[p.value[0]]}<br/>${hm.y_name}=${hm.y_values[p.value[1]]}<br/>${metricName}: ${Number(p.value[2]).toFixed(2)}`
      },
      grid: { top: 40, left: 70, right: 100, bottom: 50 },
      xAxis: { type: 'category', name: hm.x_name, data: hm.x_values.map(String) },
      yAxis: { type: 'category', name: hm.y_name, data: hm.y_values.map(String) },
      visualMap: {
        min: Math.min(...vals),
        max: Math.max(...vals),
        calculable: true,
        orient: 'vertical',
        right: 10,
        top: 'center',
        inRange: { color: [colors.loss, colors.warning, colors.profit] }
      },
      series: [{
        type: 'heatmap',
        data,
        label: { show: true, formatter: (p: any) => Number(p.value[2]).toFixed(2) },
        emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.4)' } }
      }]
    };
  };

  // 🔬 拼接OOS净值 vs OOS买入持有（灰色虚线），按日期对齐
  const getWalkForwardChartOption = () => {
    if (!wfResult || !wfResult.stitched_oos_curve.length) return {};
    const curve = wfResult.stitched_oos_curve;
    const dates = curve.map(d => d.date);
    const bhMap = new Map(wfResult.oos_buy_hold_curve.map(p => [p.date, p.value]));

    const series: any[] = [
      {
        name: '拼接OOS净值',
        type: 'line',
        data: curve.map(d => d.value),
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2, color: colors.primary },
        areaStyle: { opacity: 0.12, color: colors.primary }
      },
      {
        name: 'OOS买入持有',
        type: 'line',
        data: dates.map(d => bhMap.get(d) ?? null),
        smooth: true,
        showSymbol: false,
        connectNulls: true,
        lineStyle: { width: 2, color: colors.chartNeutral, type: 'dashed' },
        itemStyle: { color: colors.chartNeutral }
      }
    ];

    return {
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          const arr = Array.isArray(params) ? params : [params];
          const lines = arr.map((p: any) =>
            `${p.marker}${p.seriesName}: $${Number(p.value).toLocaleString()}`);
          return [arr[0]?.name, ...lines].join('<br/>');
        }
      },
      legend: { top: 0 },
      grid: { top: 40, left: 70, right: 20, bottom: 50 },
      xAxis: { type: 'category', data: dates },
      yAxis: { type: 'value', name: '复合净值 ($)', scale: true },
      dataZoom: [
        { type: 'inside' },
        { type: 'slider', height: 20, bottom: 0 }
      ],
      series
    };
  };

  const tradeColumns = [
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      render: (action: string) => (
        <Tag color={action === 'buy' ? 'green' : 'red'}>
          {action === 'buy' ? '买入' : '卖出'}
        </Tag>
      )
    },
    {
      title: '价格',
      dataIndex: 'price',
      key: 'price',
      render: (price: number) => `$${price.toFixed(2)}`
    },
    {
      title: '数量',
      dataIndex: 'shares',
      key: 'shares',
    },
    {
      title: '收益率',
      dataIndex: 'profit_pct',
      key: 'profit_pct',
      render: (pct: number | undefined) => {
        if (pct === undefined) return '-';
        return (
          <span style={{ color: pct >= 0 ? colors.profit : colors.loss }}>
            {pct >= 0 ? '+' : ''}{(pct * 100).toFixed(2)}%
          </span>
        );
      }
    }
  ];

  // 对比表格列（超额列红绿着色）
  const compareColumns = [
    {
      title: '策略',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: CompareRow) =>
        record.key === 'buy_hold'
          ? <Tag color="default">{name}（基准）</Tag>
          : <b>{name}</b>
    },
    {
      title: '总收益',
      dataIndex: 'total_return',
      key: 'total_return',
      render: (v: number) => (
        <span style={{ color: pctColor(v) }}>{v >= 0 ? '+' : ''}{v.toFixed(2)}%</span>
      )
    },
    {
      title: '年化收益',
      dataIndex: 'annual_return',
      key: 'annual_return',
      render: (v: number) => (
        <span style={{ color: pctColor(v) }}>{v >= 0 ? '+' : ''}{v.toFixed(2)}%</span>
      )
    },
    {
      title: '最大回撤',
      dataIndex: 'max_drawdown',
      key: 'max_drawdown',
      render: (v: number) => <span style={{ color: colors.loss }}>{v.toFixed(2)}%</span>
    },
    {
      title: '夏普比率',
      dataIndex: 'sharpe_ratio',
      key: 'sharpe_ratio',
      render: (v: number) => v.toFixed(2)
    },
    {
      title: '胜率',
      dataIndex: 'win_rate',
      key: 'win_rate',
      render: (v: number) => `${v.toFixed(2)}%`
    },
    {
      title: '交易次数',
      dataIndex: 'trade_count',
      key: 'trade_count'
    },
    {
      title: '总手续费',
      dataIndex: 'total_fees',
      key: 'total_fees',
      render: (v: number) => `$${v.toFixed(2)}`
    },
    {
      title: '相对持有超额',
      dataIndex: 'excess_vs_buy_hold',
      key: 'excess_vs_buy_hold',
      render: (v: number) => (
        <span style={{ color: pctColor(v), fontWeight: 600 }}>
          {v > 0 ? '+' : ''}{v.toFixed(2)}%
        </span>
      )
    }
  ];

  // 🎯 寻优Top5表格列
  const optimizeColumns = [
    {
      title: '#',
      key: 'rank',
      width: 40,
      render: (_: any, __: OptimizeRow, idx: number) => idx + 1
    },
    {
      title: '参数组合',
      dataIndex: 'params',
      key: 'params',
      render: (p: Record<string, number>) => <code>{fmtParams(p)}</code>
    },
    {
      title: '总收益',
      dataIndex: 'total_return',
      key: 'total_return',
      render: (v: number) => (
        <span style={{ color: pctColor(v) }}>{v >= 0 ? '+' : ''}{v.toFixed(2)}%</span>
      )
    },
    {
      title: '年化收益',
      dataIndex: 'annual_return',
      key: 'annual_return',
      render: (v: number) => (
        <span style={{ color: pctColor(v) }}>{v >= 0 ? '+' : ''}{v.toFixed(2)}%</span>
      )
    },
    {
      title: '夏普比率',
      dataIndex: 'sharpe_ratio',
      key: 'sharpe_ratio',
      render: (v: number) => v.toFixed(2)
    },
    {
      title: '最大回撤',
      dataIndex: 'max_drawdown',
      key: 'max_drawdown',
      render: (v: number) => <span style={{ color: colors.loss }}>{v.toFixed(2)}%</span>
    },
    {
      title: '交易次数',
      dataIndex: 'trade_count',
      key: 'trade_count'
    }
  ];

  // 🔬 Walk-Forward分段表列
  const wfColumns = [
    { title: '步骤', dataIndex: 'step', key: 'step', width: 60 },
    {
      title: '训练区间',
      dataIndex: 'train_range',
      key: 'train_range',
      render: (r: [string, string]) => `${r[0]} ~ ${r[1]}`
    },
    {
      title: '测试区间',
      dataIndex: 'test_range',
      key: 'test_range',
      render: (r: [string, string]) => `${r[0]} ~ ${r[1]}`
    },
    {
      title: '最优参数（样本内夏普）',
      dataIndex: 'best_params',
      key: 'best_params',
      render: (p: Record<string, number>, record: WFSegment) => (
        <span><code>{fmtParams(p)}</code>（IS夏普 {record.is_sharpe.toFixed(2)}）</span>
      )
    },
    {
      title: '样本外收益',
      dataIndex: 'oos_return',
      key: 'oos_return',
      render: (v: number) => (
        <span style={{ color: pctColor(v), fontWeight: 600 }}>
          {v >= 0 ? '+' : ''}{v.toFixed(2)}%
        </span>
      )
    },
    {
      title: 'OOS夏普',
      dataIndex: 'oos_sharpe',
      key: 'oos_sharpe',
      render: (v: number) => v.toFixed(2)
    },
    {
      title: 'OOS回撤',
      dataIndex: 'oos_max_drawdown',
      key: 'oos_max_drawdown',
      render: (v: number) => <span style={{ color: colors.loss }}>{v.toFixed(2)}%</span>
    },
    {
      title: '跑赢持有',
      dataIndex: 'beats_buy_hold',
      key: 'beats_buy_hold',
      render: (ok: boolean, record: WFSegment) => (
        <>
          <Tag color={ok ? 'green' : 'red'}>{ok ? '✓ 跑赢' : '✗ 跑输'}</Tag>
          <span style={{ fontSize: 12, color: colors.textSecondary }}>持有{record.oos_buy_hold_return >= 0 ? '+' : ''}{record.oos_buy_hold_return.toFixed(2)}%</span>
        </>
      )
    }
  ];

  return (
    <div>
      <h2>🧪 策略回测</h2>

      <Row gutter={16}>
        <Col xs={24} lg={16}>
          <Card title="回测配置" style={{ marginBottom: 16 }}>
            <Form
              form={form}
              layout="vertical"
              initialValues={{
                strategy: 'linear',
                period: '1y',
                initial_capital: 100000
              }}
            >
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="stock_code"
                    label="股票代码"
                    rules={[{ required: true, message: '请输入股票代码' }]}
                  >
                    <Search
                      placeholder="输入股票代码搜索"
                      onSearch={handleSearch}
                      enterButton={<><SearchOutlined /> 搜索</>}
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="strategy"
                    label="选择策略"
                    rules={[{ required: true, message: '请选择策略' }]}
                  >
                    <Select placeholder="选择回测策略">
                      {strategies.map(s => (
                        <Option key={s.id} value={s.id}>
                          {s.name} - {s.description}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              {searchResults.length > 0 && (
                <Form.Item label="选择股票">
                  <Space wrap>
                    {searchResults.map((stock) => (
                      <Tag
                        key={stock.code}
                        color={selectedStock?.code === stock.code ? 'blue' : 'default'}
                        style={{ cursor: 'pointer' }}
                        onClick={() => handleSelectStock(stock)}
                      >
                        {stock.code} {stock.name}
                      </Tag>
                    ))}
                  </Space>
                </Form.Item>
              )}

              <Row gutter={16}>
                <Col xs={24} md={8}>
                  <Form.Item name="period" label="回测周期">
                    <Select
                      disabled={!!dateRangeWatch}
                      options={[
                        { value: '1y', label: '近1年' },
                        { value: '3y', label: '近3年' },
                        { value: '5y', label: '近5年' },
                      ]}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item name="date_range" label="自定义时间段（可选，优先于周期）">
                    <DatePicker.RangePicker style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item
                    name="initial_capital"
                    label="初始资金"
                    rules={[{ required: true }]}
                  >
                    <InputNumber
                      style={{ width: '100%' }}
                      min={10000}
                      step={10000}
                      formatter={value => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                      parser={value => Number(value?.replace(/\$\s?|(,*)/g, '') || 0) as any}
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item>
                <Space size="middle">
                  <Button
                    type="primary"
                    icon={<ExperimentOutlined />}
                    onClick={handleRunBacktest}
                    loading={loading}
                    size="large"
                  >
                    开始回测
                  </Button>
                  <Button
                    onClick={handleRunCompare}
                    loading={compareLoading}
                    disabled={!selectedStock}
                    size="large"
                  >
                    ⚡ 一键对比4策略
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </Card>

          {backtestResult && (
            <Card title="📊 权益曲线">
              <ReactEChartsCore echarts={echarts} option={getEquityCurveOption()} style={{ height: 300 }} />
            </Card>
          )}

          {compareResult && (
            <Card title={`⚡ 4策略对比 vs 买入持有 · ${compareResult.stock_code}`} style={{ marginTop: 16 }}>
              <ReactEChartsCore echarts={echarts} option={getCompareChartOption()} style={{ height: 380 }} />
              <Table
                style={{ marginTop: 16, whiteSpace: 'nowrap' }}
                columns={compareColumns}
                dataSource={compareResult.comparison}
                rowKey="key"
                pagination={false}
                size="small"
                scroll={{ x: 'max-content' }}
              />
            </Card>
          )}

          {/* 🎯 参数寻优面板 */}
          <Card title={`🎯 参数寻优${optResult ? ` · ${optResult.stock_code} · ${periodLabel(optResult.period)} · 资金$${(optResult.initial_capital ?? 0).toLocaleString()}` : ''}`} style={{ marginTop: 16 }}>
            <Space wrap style={{ marginBottom: 16 }}>
              <Select value={optStrategy} onChange={setOptStrategy} style={{ width: 240 }}>
                {strategies.map(s => (
                  <Option key={s.id} value={s.id}>
                    {s.name} - {s.description}
                  </Option>
                ))}
              </Select>
              <Button
                type="primary"
                ghost
                icon={<AimOutlined />}
                loading={optLoading}
                disabled={!selectedStock}
                onClick={handleRunOptimize}
              >
                开始寻优
              </Button>
            </Space>

            {optResult && (
              <>
                <Tag color="gold" style={{ marginBottom: 12 }}>
                  最优参数：{fmtParams(optResult.best.params)}
                  （{METRIC_LABEL[optResult.metric] || optResult.metric} {Number(optResult.best.sharpe_ratio).toFixed(2)}）
                </Tag>
                <ReactEChartsCore echarts={echarts} option={getOptimizeHeatmapOption()} style={{ height: 320 }} />
                <div style={{ margin: '8px 0 4px', color: colors.textSecondary }}>
                  热力图：x={optResult.heatmap.x_name}，y={optResult.heatmap.y_name}，颜色=夏普比率；下表为Top5最优参数组合
                </div>
                <Table
                  style={{ whiteSpace: 'nowrap' }}
                  columns={optimizeColumns}
                  dataSource={optResult.results.slice(0, 5)}
                  rowKey={(r) => fmtParams(r.params)}
                  pagination={false}
                  size="small"
                  scroll={{ x: 'max-content' }}
                />
              </>
            )}
          </Card>

          {/* 🔬 Walk-Forward验证面板 */}
          <Card title={`🔬 Walk-Forward验证${wfResult ? ` · ${wfResult.stock_code} · ${periodLabel(wfResult.period)} · 资金$${(wfResult.initial_capital ?? 0).toLocaleString()}` : ''}`} style={{ marginTop: 16 }}>
            <Space wrap style={{ marginBottom: 16 }}>
              <Select value={wfStrategy} onChange={setWfStrategy} style={{ width: 240 }}>
                {strategies.map(s => (
                  <Option key={s.id} value={s.id}>
                    {s.name} - {s.description}
                  </Option>
                ))}
              </Select>
              <span>段数：</span>
              <InputNumber
                min={1}
                max={4}
                value={wfSegments}
                onChange={(v) => setWfSegments(Number(v) || 2)}
              />
              <Button
                type="primary"
                ghost
                icon={<PlayCircleOutlined />}
                loading={wfLoading}
                disabled={!selectedStock}
                onClick={handleRunWalkForward}
              >
                开始验证
              </Button>
            </Space>

            {wfResult && (
              <>
                <Descriptions size="small" column={3} style={{ marginBottom: 12 }}>
                  <Descriptions.Item label="平均样本外收益">
                    <span style={{ color: pctColor(wfResult.summary.avg_oos_return), fontWeight: 600 }}>
                      {wfResult.summary.avg_oos_return >= 0 ? '+' : ''}{wfResult.summary.avg_oos_return.toFixed(2)}%
                    </span>
                  </Descriptions.Item>
                  <Descriptions.Item label="平均OOS夏普">
                    {wfResult.summary.avg_oos_sharpe.toFixed(2)}
                  </Descriptions.Item>
                  <Descriptions.Item label="跑赢段数">
                    {wfResult.summary.win_segments}/{wfResult.summary.total_segments}
                  </Descriptions.Item>
                </Descriptions>
                <ReactEChartsCore echarts={echarts} option={getWalkForwardChartOption()} style={{ height: 320 }} />
                <Table
                  style={{ marginTop: 16, whiteSpace: 'nowrap' }}
                  columns={wfColumns}
                  dataSource={wfResult.segments}
                  rowKey="step"
                  pagination={false}
                  size="small"
                  scroll={{ x: 'max-content' }}
                />
              </>
            )}
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          {backtestResult ? (
            <>
              <Card title="📈 回测结果" style={{ marginBottom: 16 }}>
                <Descriptions column={1}>
                  <Descriptions.Item label="股票代码">
                    {backtestResult.stock_code}
                  </Descriptions.Item>
                  <Descriptions.Item label="策略">
                    {strategies.find(s => s.id === backtestResult.strategy)?.name}
                  </Descriptions.Item>
                  <Descriptions.Item label="回测周期">
                    {backtestResult.date_range
                      ? backtestResult.date_range
                      : backtestResult.period === '3y' ? '近3年' : backtestResult.period === '5y' ? '近5年' : '近1年'}
                  </Descriptions.Item>
                </Descriptions>

                <Divider />

                <Row gutter={16}>
                  <Col span={12}>
                    <Statistic
                      title="总收益"
                      value={backtestResult.total_return}
                      precision={2}
                      suffix="%"
                      valueStyle={{
                        color: backtestResult.total_return >= 0 ? colors.profit : colors.loss
                      }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="年化收益"
                      value={backtestResult.annual_return}
                      precision={2}
                      suffix="%"
                      valueStyle={{
                        color: backtestResult.annual_return >= 0 ? colors.profit : colors.loss
                      }}
                    />
                  </Col>
                </Row>

                {backtestResult.buy_hold_return != null && (() => {
                  const excess = backtestResult.total_return - backtestResult.buy_hold_return!;
                  return (
                    <Statistic
                      title="相对买入持有（超额）"
                      value={excess}
                      precision={2}
                      suffix="%"
                      prefix={excess > 0 ? '+' : ''}
                      style={{ marginTop: 16 }}
                      valueStyle={{ color: excess > 0 ? colors.profit : excess < 0 ? colors.loss : colors.textSecondary }}
                    />
                  );
                })()}

                <Row gutter={16} style={{ marginTop: 16 }}>
                  <Col span={12}>
                    <Statistic
                      title="最大回撤"
                      value={backtestResult.max_drawdown}
                      precision={2}
                      suffix="%"
                      valueStyle={{ color: colors.loss }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="夏普比率"
                      value={backtestResult.sharpe_ratio}
                      precision={2}
                    />
                  </Col>
                </Row>

                <Row gutter={16} style={{ marginTop: 16 }}>
                  <Col span={12}>
                    <Statistic
                      title="胜率"
                      value={backtestResult.win_rate}
                      precision={2}
                      suffix="%"
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="交易次数"
                      value={backtestResult.trade_count}
                    />
                  </Col>
                </Row>

                <Divider />

                <Descriptions column={1}>
                  <Descriptions.Item label="初始资金">
                    ${backtestResult.initial_capital?.toLocaleString() ?? '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="最终资金">
                    ${backtestResult.final_value?.toLocaleString() ?? '-'}
                  </Descriptions.Item>
                </Descriptions>
              </Card>

              <Card title="📝 交易记录">
                <Table
                  style={{ whiteSpace: 'nowrap' }}
                  columns={tradeColumns}
                  dataSource={backtestResult.trades}
                  rowKey={(record) => `${record.date}-${record.action}-${record.price}`}
                  pagination={false}
                  size="small"
                  scroll={{ x: 'max-content', y: 300 }}
                />
              </Card>
            </>
          ) : (
            <Card>
              <div style={{ textAlign: 'center', padding: 50, color: colors.textSecondary }}>
                配置参数后点击"开始回测"
              </div>
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
};

export default Backtest;
