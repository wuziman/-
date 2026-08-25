import { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConfigProvider, Spin } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import MainLayout from './components/MainLayout';
import ErrorBoundary from './components/ErrorBoundary';
import { colors } from './theme/tokens';

// 路由级代码分割：首页不再打包回测/分析页与echarts，进入对应页面时才加载
const Home = lazy(() => import('./pages/Home'));
const Analysis = lazy(() => import('./pages/Analysis'));
const Portfolio = lazy(() => import('./pages/Portfolio'));
const Backtest = lazy(() => import('./pages/Backtest'));
const AIPick = lazy(() => import('./pages/AIPick'));

function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          // 与 DESIGN.md/tokens.ts 对齐；colorLink 用更深的蓝保证正文链接对比度≥4.5:1
          colorPrimary: colors.primary,
          colorInfo: colors.primary,
          colorLink: '#0958d9',
        },
      }}
    >
      <Router>
        <MainLayout>
          <ErrorBoundary>
            <Suspense
              fallback={
                <div style={{ textAlign: 'center', padding: 80 }}>
                  <Spin size="large" />
                </div>
              }
            >
              <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/analysis" element={<Analysis />} />
              <Route path="/portfolio" element={<Portfolio />} />
              <Route path="/backtest" element={<Backtest />} />
              <Route path="/ai-pick" element={<AIPick />} />
              </Routes>
            </Suspense>
          </ErrorBoundary>
        </MainLayout>
      </Router>
    </ConfigProvider>
  );
}

export default App;
