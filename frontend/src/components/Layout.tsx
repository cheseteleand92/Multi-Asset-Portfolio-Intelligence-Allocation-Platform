import { NavLink, Outlet } from 'react-router-dom'
import { BarChart2, AlertTriangle, Radio, TrendingUp, Settings } from 'lucide-react'
import Header from './Header'

const nav = [
  { to: '/portfolio', icon: BarChart2, label: 'Portfolio' },
  { to: '/risk', icon: AlertTriangle, label: 'Risk' },
  { to: '/signals', icon: Radio, label: 'Signals' },
  { to: '/backtest', icon: TrendingUp, label: 'Backtest' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Layout() {
  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100">
      <aside className="w-16 flex flex-col items-center py-6 gap-6 bg-zinc-900 border-r border-zinc-800">
        {nav.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            title={label}
            className={({ isActive }) =>
              `p-2 rounded-lg transition-colors ${
                isActive
                  ? 'bg-zinc-700 text-white'
                  : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
              }`
            }
          >
            <Icon size={20} />
          </NavLink>
        ))}
      </aside>
      <div className="flex flex-col flex-1 overflow-hidden">
        <Header />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
