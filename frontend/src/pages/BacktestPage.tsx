import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import { backtestApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'

interface NavPoint { date: string; nav: number }
interface RunSummary { run_id: number; strategy: string; created_at: string }

export default function BacktestPage() {
  const { selectedPortfolioId } = useAppStore()
  const qc = useQueryClient()
  const [strategy, setStrategy] = useState('hrp')
  const [costBps, setCostBps] = useState('10')
  const [lookback, setLookback] = useState('63')
  const [activeRunId, setActiveRunId] = useState<number | null>(null)

  const { data: runs = [] } = useQuery<RunSummary[]>({
    queryKey: ['backtests', selectedPortfolioId],
    queryFn: () => backtestApi.list(selectedPortfolioId!),
    enabled: !!selectedPortfolioId,
  })

  const { data: runDetail } = useQuery({
    queryKey: ['backtest-detail', activeRunId],
    queryFn: () => backtestApi.get(activeRunId!),
    enabled: !!activeRunId,
  })

  const createRun = useMutation({
    mutationFn: () =>
      backtestApi.create({
        portfolio_id: selectedPortfolioId,
        strategy,
        cost_bps: Number(costBps),
        lookback_days: Number(lookback),
      }),
    onSuccess: (data: { run_id: number }) => {
      setActiveRunId(data.run_id)
      void qc.invalidateQueries({ queryKey: ['backtests', selectedPortfolioId] })
    },
  })

  if (!selectedPortfolioId) return <div className="text-zinc-500 text-sm">Select a portfolio.</div>

  const navData: NavPoint[] = runDetail?.nav ?? []

  return (
    <div className="space-y-6">
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-sm">Run Backtest</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-3 flex-wrap items-end">
            <div>
              <p className="text-xs text-zinc-400 mb-1">Strategy</p>
              <Select value={strategy} onValueChange={setStrategy}>
                <SelectTrigger className="w-40 bg-zinc-800 border-zinc-700 text-sm h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="hrp">HRP</SelectItem>
                  <SelectItem value="equal_weight">Equal Weight</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <p className="text-xs text-zinc-400 mb-1">Cost (bps)</p>
              <input
                type="number"
                value={costBps}
                onChange={(e) => setCostBps(e.target.value)}
                className="w-20 h-8 rounded bg-zinc-800 border border-zinc-700 text-sm px-2 text-zinc-100"
              />
            </div>
            <div>
              <p className="text-xs text-zinc-400 mb-1">Lookback days</p>
              <input
                type="number"
                value={lookback}
                onChange={(e) => setLookback(e.target.value)}
                className="w-24 h-8 rounded bg-zinc-800 border border-zinc-700 text-sm px-2 text-zinc-100"
              />
            </div>
            <Button size="sm" className="h-8" onClick={() => createRun.mutate()} disabled={createRun.isPending}>
              {createRun.isPending ? 'Running…' : 'Run'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {navData.length > 0 && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-sm">
              NAV — {runDetail?.strategy?.toUpperCase()} (run #{activeRunId})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={navData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: '#71717a', fontSize: 10 }}
                  tickFormatter={(v: string) => v.slice(0, 7)}
                  interval="preserveStartEnd"
                />
                <YAxis tick={{ fill: '#71717a', fontSize: 10 }} domain={['auto', 'auto']} />
                <Tooltip
                  contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', fontSize: 11 }}
                  formatter={(v: unknown) => (v as number).toFixed(2)}
                />
                <Line type="monotone" dataKey="nav" stroke="#6366f1" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {runs.length > 0 && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-sm">Past Runs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {runs.map((r) => (
                <button
                  key={r.run_id}
                  onClick={() => setActiveRunId(r.run_id)}
                  className={`w-full text-left text-xs px-3 py-2 rounded transition-colors ${
                    activeRunId === r.run_id
                      ? 'bg-zinc-700 text-white'
                      : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
                  }`}
                >
                  <span className="font-mono">#{r.run_id}</span>
                  <span className="ml-2 uppercase text-zinc-300">{r.strategy}</span>
                  <span className="ml-2 text-zinc-500">{r.created_at.slice(0, 10)}</span>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
