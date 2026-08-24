import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import MainLayout from './components/MainLayout';
import ErrorBoundary from './components/ErrorBoundary';
import Home from './pages/Home';
import Analysis from './pages/Analysis';
import Portfolio from './pages/Portfolio';
import Backtest from './pages/Backtest';
import AIPick from './pages/AIPick';

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <Router>
        <MainLayout>
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/analysis" element={<Analysis />} />
              <Route path="/portfolio" element={<Portfolio />} />
              <Route path="/backtest" element={<Backtest />} />
              <Route path="/ai-pick" element={<AIPick />} />
            </Routes>
          </ErrorBoundary>
        </MainLayout>
      </Router>
    </ConfigProvider>
  );
}

export default App;
