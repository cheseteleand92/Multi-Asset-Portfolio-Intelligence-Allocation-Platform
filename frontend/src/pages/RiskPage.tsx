import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts'
import { analyticsApi, stressApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'

interface RiskData {
  var_95?: number
  es_95?: number
  volatility?: number
  max_drawdown?: number
  trc?: Record<string, number>
}

interface StressResult {
  total_pnl: number
  pnl_pct: number
}

export default function RiskPage() {
  const { selectedPortfolioId } = useAppStore()
  const [scenarioId, setScenarioId] = useState<string>('')
  const [stressResult, setStressResult] = useState<StressResult | null>(null)

  const { data: risk } = useQuery<RiskData>({
    queryKey: ['risk', selectedPortfolioId],
    queryFn: () => analyticsApi.getRisk(selectedPortfolioId!),
    enabled: !!selectedPortfolioId,
  })
  const { data: scenarios = [] } = useQuery<{ id: string; description: string }[]>({
    queryKey: ['scenarios'],
    queryFn: stressApi.getScenarios,
  })

  const runStress = useMutation({
    mutationFn: () => stressApi.run(selectedPortfolioId!, scenarioId),
    onSuccess: (data) => setStressResult(data as StressResult),
  })

  if (!selectedPortfolioId) return <div className="text-muted-foreground text-sm">Select a portfolio.</div>

  const trcData = risk?.trc
    ? Object.entries(risk.trc).map(([k, v]) => ({ ticker: k, trc: Number(v) }))
    : []

  const metrics = [
    { label: 'VaR 95%', value: risk?.var_95, color: 'text-amber-400' },
    { label: 'ES 95%', value: risk?.es_95, color: 'text-orange-400' },
    { label: 'Volatility', value: risk?.volatility, color: 'text-blue-400' },
    { label: 'Max Drawdown', value: risk?.max_drawdown, color: 'text-red-400' },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-4">
        {metrics.map(({ label, value, color }) => (
          <Card key={label} className="bg-card border-border">
            <CardHeader className="pb-1">
              <CardTitle className="text-xs text-muted-foreground">{label}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className={`text-xl font-bold ${color}`}>
                {value != null ? `${(value * 100).toFixed(2)}%` : '—'}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="text-sm">Risk Contribution by Position</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={trcData} layout="vertical">
              <XAxis
                type="number"
                tick={{ fill: '#71717a', fontSize: 11 }}
                tickFormatter={(v: unknown) => `${((v as number) * 100).toFixed(1)}%`}
              />
              <YAxis type="category" dataKey="ticker" tick={{ fill: '#a1a1aa', fontSize: 11 }} width={110} />
              <Tooltip
                formatter={(v: unknown) => `${((v as number) * 100).toFixed(2)}%`}
                contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }}
              />
              <Bar dataKey="trc" fill="#6366f1" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="text-sm">Stress Testing</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-3 items-end">
            <Select value={scenarioId} onValueChange={setScenarioId}>
              <SelectTrigger className="w-64 bg-muted/40 border-border text-sm h-8">
                <SelectValue placeholder="Select scenario" />
              </SelectTrigger>
              <SelectContent>
                {scenarios.map((s) => (
                  <SelectItem key={s.id} value={s.id}>{s.description}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              size="sm"
              className="h-8"
              onClick={() => runStress.mutate()}
              disabled={!scenarioId || runStress.isPending}
            >
              Run
            </Button>
          </div>
          {stressResult && (
            <div className="flex gap-4">
              <div className="bg-muted/40 rounded p-3">
                <p className="text-xs text-muted-foreground">Total P&amp;L</p>
                <p className={`text-lg font-bold ${stressResult.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  ${stressResult.total_pnl.toLocaleString()}
                </p>
              </div>
              <div className="bg-muted/40 rounded p-3">
                <p className="text-xs text-muted-foreground">P&amp;L %</p>
                <p className={`text-lg font-bold ${stressResult.pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {(stressResult.pnl_pct * 100).toFixed(2)}%
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

