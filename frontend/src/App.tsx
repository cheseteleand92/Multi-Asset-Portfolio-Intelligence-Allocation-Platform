import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from './lib/queryClient'
import Layout from './components/Layout'
import PortfolioPage from './pages/PortfolioPage'
import RiskPage from './pages/RiskPage'
import SignalsPage from './pages/SignalsPage'
import BacktestPage from './pages/BacktestPage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Navigate to="/portfolio" replace />} />
            <Route path="portfolio" element={<PortfolioPage />} />
            <Route path="risk" element={<RiskPage />} />
            <Route path="signals" element={<SignalsPage />} />
            <Route path="backtest" element={<BacktestPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
