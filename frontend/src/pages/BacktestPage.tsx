import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts'
import { backtestApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'

interface NavPoint { date: string; nav: number }
interface RunSummary { run_id: number; strategy: string; created_at: string }
interface Strategy { id: string; label: string }
interface Benchmark { id: string; label: string }
interface BacktestDetail {
  run_id: number
  strategy: string
  nav: NavPoint[]
  benchmark?: NavPoint[]
  params?: { benchmark?: string }
}

const FALLBACK_STRATEGIES: Strategy[] = [
  { id: 'hrp', label: 'Hierarchical Risk Parity' },
  { id: 'equal_weight', label: 'Equal Weight' },
  { id: 'mean_variance', label: 'Mean-Variance' },
  { id: 'erc', label: 'Equal Risk Contribution' },
]

const FALLBACK_BENCHMARKS: Benchmark[] = [
  { id: 'none', label: 'No Benchmark' },
  { id: 'equal_weight', label: 'Equal Weight' },
  { id: 'hrp', label: 'Hierarchical Risk Parity' },
  { id: 'mean_variance', label: 'Mean-Variance' },
  { id: 'erc', label: 'Equal Risk Contribution' },
]

function computeStats(navData: NavPoint[]) {
  if (navData.length < 2) return null
  const first = navData[0].nav
  const last = navData[navData.length - 1].nav
  const totalReturn = first > 0 ? (last - first) / first : 0

  let peak = navData[0].nav
  let maxDrawdown = 0
  const dailyReturns: number[] = []

  for (let i = 1; i < navData.length; i += 1) {
    const prev = navData[i - 1].nav
    const curr = navData[i].nav
    if (curr > peak) peak = curr
    const dd = peak > 0 ? (curr - peak) / peak : 0
    if (dd < maxDrawdown) maxDrawdown = dd
    if (prev > 0) {
      dailyReturns.push((curr - prev) / prev)
    }
  }

  const mean = dailyReturns.reduce((s, v) => s + v, 0) / Math.max(dailyReturns.length, 1)
  const variance = dailyReturns.reduce((s, v) => s + (v - mean) ** 2, 0) / Math.max(dailyReturns.length, 1)
  const annualVol = Math.sqrt(variance) * Math.sqrt(252)

  return { totalReturn, maxDrawdown, annualVol }
}

function downloadBacktestCsv(
  filename: string,
  strategySeries: NavPoint[],
  benchmarkSeries: NavPoint[],
) {
  const byDate = new Map<string, { strategy?: number; benchmark?: number }>()

  for (const p of strategySeries) {
    byDate.set(p.date, { ...(byDate.get(p.date) ?? {}), strategy: p.nav })
  }
  for (const p of benchmarkSeries) {
    byDate.set(p.date, { ...(byDate.get(p.date) ?? {}), benchmark: p.nav })
  }

  const lines = ['date,strategy_nav,benchmark_nav']
  const dates = Array.from(byDate.keys()).sort()
  for (const d of dates) {
    const row = byDate.get(d) ?? {}
    lines.push(`${d},${row.strategy ?? ''},${row.benchmark ?? ''}`)
  }

  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export default function BacktestPage() {
  const { selectedPortfolioId } = useAppStore()
  const qc = useQueryClient()
  const [strategy, setStrategy] = useState('hrp')
  const [benchmark, setBenchmark] = useState('equal_weight')
  const [costBps, setCostBps] = useState('10')
  const [lookback, setLookback] = useState('63')
  const [activeRunId, setActiveRunId] = useState<number | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const { data: strategyOptions = FALLBACK_STRATEGIES } = useQuery<Strategy[]>({
    queryKey: ['backtest-strategies'],
    queryFn: backtestApi.listStrategies,
  })
  const { data: benchmarkOptions = FALLBACK_BENCHMARKS } = useQuery<Benchmark[]>({
    queryKey: ['backtest-benchmarks'],
    queryFn: backtestApi.listBenchmarks,
  })

  const { data: runs = [] } = useQuery<RunSummary[]>({
    queryKey: ['backtests', selectedPortfolioId],
    queryFn: () => backtestApi.list(selectedPortfolioId!),
    enabled: !!selectedPortfolioId,
  })

  const sortedRuns = useMemo(
    () => [...runs].sort((a, b) => b.created_at.localeCompare(a.created_at)),
    [runs],
  )

  const selectedRunId = activeRunId ?? (sortedRuns[0]?.run_id ?? null)

  const { data: runDetail, isLoading: detailLoading } = useQuery<BacktestDetail>({
    queryKey: ['backtest-detail', selectedRunId],
    queryFn: () => backtestApi.get(selectedRunId!),
    enabled: !!selectedRunId,
  })

  const createRun = useMutation({
    mutationFn: () =>
      backtestApi.create({
        portfolio_id: selectedPortfolioId,
        strategy,
        benchmark,
        cost_bps: Number(costBps),
        lookback_days: Number(lookback),
      }),
    onSuccess: (data: { run_id: number }) => {
      setErrorMsg(null)
      setActiveRunId(data.run_id)
      void qc.invalidateQueries({ queryKey: ['backtests', selectedPortfolioId] })
    },
    onError: (error: { response?: { data?: { detail?: string } } }) => {
      setErrorMsg(error.response?.data?.detail ?? 'Backtest failed. Check data and parameters.')
    },
  })

  if (!selectedPortfolioId) return <div className="text-muted-foreground text-sm">Select a portfolio.</div>

  const navData: NavPoint[] = runDetail?.nav ?? []
  const benchmarkData: NavPoint[] = runDetail?.benchmark ?? []
  const stats = computeStats(navData)
  const benchmarkName = benchmarkOptions.find((b) => b.id === (runDetail?.params?.benchmark ?? benchmark))?.label ?? 'Benchmark'
  const mergedChartData = navData.map((p) => {
    const benchmark = benchmarkData.find((b) => b.date === p.date)?.nav
    return { ...p, benchmark }
  })
  const allNavValues = [
    ...mergedChartData.map((d) => d.nav),
    ...mergedChartData.map((d) => d.benchmark).filter((v): v is number => typeof v === 'number'),
  ]
  const minNav = allNavValues.length ? Math.min(...allNavValues) : 0
  const maxNav = allNavValues.length ? Math.max(...allNavValues) : 0

  return (
    <div className="space-y-6">
      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="text-sm">Run Backtest</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-3 flex-wrap items-end">
            <div>
              <p className="text-xs text-muted-foreground mb-1">Strategy</p>
              <Select value={strategy} onValueChange={setStrategy}>
                <SelectTrigger className="w-56 bg-muted/40 border-border text-sm h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {strategyOptions.map((opt) => (
                    <SelectItem key={opt.id} value={opt.id}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Benchmark</p>
              <Select value={benchmark} onValueChange={setBenchmark}>
                <SelectTrigger className="w-56 bg-muted/40 border-border text-sm h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {benchmarkOptions.map((opt) => (
                    <SelectItem key={opt.id} value={opt.id}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Cost (bps)</p>
              <input
                type="number"
                value={costBps}
                onChange={(e) => setCostBps(e.target.value)}
                className="w-20 h-8 rounded bg-muted/40 border border-border text-sm px-2 text-foreground"
              />
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Lookback days</p>
              <input
                type="number"
                value={lookback}
                onChange={(e) => setLookback(e.target.value)}
                className="w-24 h-8 rounded bg-muted/40 border border-border text-sm px-2 text-foreground"
              />
            </div>
            <Button size="sm" className="h-8" onClick={() => createRun.mutate()} disabled={createRun.isPending}>
              {createRun.isPending ? 'Running…' : 'Run'}
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-8 border-border bg-muted/40 text-xs"
              onClick={() => downloadBacktestCsv(`backtest_run_${selectedRunId ?? 'latest'}.csv`, navData, benchmarkData)}
              disabled={navData.length === 0}
            >
              Export CSV
            </Button>
          </div>
          {errorMsg && <p className="text-xs text-destructive">{errorMsg}</p>}
        </CardContent>
      </Card>

      {detailLoading && selectedRunId && (
        <div className="text-xs text-muted-foreground">Loading run detail…</div>
      )}

      {stats && (
        <div className="grid grid-cols-3 gap-4">
          <Card className="bg-card border-border">
            <CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground">Total Return</CardTitle></CardHeader>
            <CardContent>
              <p className={`text-xl font-semibold ${stats.totalReturn >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {(stats.totalReturn * 100).toFixed(2)}%
              </p>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground">Max Drawdown</CardTitle></CardHeader>
            <CardContent>
              <p className="text-xl font-semibold text-amber-400">{(stats.maxDrawdown * 100).toFixed(2)}%</p>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground">Annualized Volatility</CardTitle></CardHeader>
            <CardContent>
              <p className="text-xl font-semibold text-sky-400">{(stats.annualVol * 100).toFixed(2)}%</p>
            </CardContent>
          </Card>
        </div>
      )}

      {navData.length > 0 && (
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="text-sm">
              NAV — {runDetail?.strategy?.toUpperCase()} (run #{selectedRunId})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={mergedChartData}>
                <defs>
                  <linearGradient id="navGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="2 4" stroke="#3f3f46" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: '#71717a', fontSize: 10 }}
                  tickFormatter={(v: string) => v.slice(2, 10)}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tick={{ fill: '#71717a', fontSize: 10 }}
                  domain={[Math.floor(minNav * 0.99), Math.ceil(maxNav * 1.01)]}
                  tickFormatter={(v: number) => v.toFixed(0)}
                />
                <ReferenceLine y={100} stroke="#52525b" strokeDasharray="4 4" />
                <Tooltip
                  contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', fontSize: 11 }}
                  labelFormatter={(label: string) => `Date: ${label}`}
                  formatter={(v: unknown, name: string) => [`${(v as number).toFixed(2)}`, name]}
                />
                <Area type="monotone" dataKey="nav" stroke="#38bdf8" fill="url(#navGradient)" strokeWidth={2.5} dot={false} />
                <Line
                  type="monotone"
                  dataKey="benchmark"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                  name={benchmarkName}
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {sortedRuns.length > 0 && (
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="text-sm">Past Runs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {sortedRuns.map((r) => (
                <button
                  key={r.run_id}
                  onClick={() => setActiveRunId(r.run_id)}
                  className={`w-full text-left text-xs px-3 py-2 rounded transition-colors ${
                    selectedRunId === r.run_id
                      ? 'bg-accent text-foreground'
                      : 'bg-muted/40 text-muted-foreground hover:bg-accent'
                  }`}
                >
                  <span className="font-mono">#{r.run_id}</span>
                  <span className="ml-2 uppercase text-foreground/80">{r.strategy}</span>
                  <span className="ml-2 text-muted-foreground">{r.created_at.slice(0, 10)}</span>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

