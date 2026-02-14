import { useEffect } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { BarChart2, Briefcase, AlertTriangle, Radio, TrendingUp, Settings } from 'lucide-react'
import Header from './Header'
import { useAppStore } from '@/lib/store'

const nav = [
  { to: '/portfolio', icon: BarChart2, label: 'Portfolio' },
  { to: '/holdings', icon: Briefcase, label: 'Holdings' },
  { to: '/risk', icon: AlertTriangle, label: 'Risk' },
  { to: '/signals', icon: Radio, label: 'Signals' },
  { to: '/backtest', icon: TrendingUp, label: 'Backtest' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Layout() {
  const { theme } = useAppStore()

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [theme])

  return (
    <div className="flex h-screen bg-background text-foreground">
      <aside className="w-16 flex flex-col items-center py-6 gap-6 bg-card border-r border-border">
        {nav.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            title={label}
            className={({ isActive }) =>
              `p-2 rounded-lg transition-colors ${
                isActive
                  ? 'bg-accent text-foreground'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent/70'
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

