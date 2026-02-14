import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts'
import { analyticsApi, stressApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'

interface RiskData {
  var?: number
  es?: number
  var_95?: number
  es_95?: number
  volatility?: number
  max_drawdown?: number
  trc?: Record<string, number>
  warnings?: string[]
  data_range?: {
    start?: string | null
    end?: string | null
    observations?: number
  }
  base_currency?: string
  fx_used?: Record<string, string>
  config_used?: {
    lookback_days: number
    return_frequency: string
    confidence_level: number
    annualization: number
  }
  risk_explainability?: {
    total_delta_volatility: number
    weight_effect: number
    market_effect: number
    interaction_effect: number
    top_contributors: Array<{ ticker: string; trc: number }>
  }
}

interface StressResult {
  total_pnl: number
  pnl_pct: number
}

export default function RiskPage() {
  const { selectedPortfolioId } = useAppStore()
  const [scenarioId, setScenarioId] = useState<string>('')
  const [stressResult, setStressResult] = useState<StressResult | null>(null)
  const [lookbackDays, setLookbackDays] = useState('252')
  const [returnFrequency, setReturnFrequency] = useState<'daily' | 'weekly'>('daily')
  const [confidenceLevel, setConfidenceLevel] = useState('0.95')
  const [baseCurrency, setBaseCurrency] = useState('USD')

  const { data: risk } = useQuery<RiskData>({
    queryKey: ['risk', selectedPortfolioId, lookbackDays, returnFrequency, confidenceLevel, baseCurrency],
    queryFn: () =>
      analyticsApi.getRisk(selectedPortfolioId!, {
        lookback_days: Number(lookbackDays),
        return_frequency: returnFrequency,
        confidence_level: Number(confidenceLevel),
        base_currency: baseCurrency,
      }),
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
    {
      label: `VaR ${Math.round((risk?.config_used?.confidence_level ?? 0.95) * 100)}%`,
      value: risk?.var ?? risk?.var_95,
      color: 'text-amber-400',
    },
    {
      label: `ES ${Math.round((risk?.config_used?.confidence_level ?? 0.95) * 100)}%`,
      value: risk?.es ?? risk?.es_95,
      color: 'text-orange-400',
    },
    { label: 'Volatility', value: risk?.volatility, color: 'text-blue-400' },
    { label: 'Max Drawdown', value: risk?.max_drawdown, color: 'text-red-400' },
  ]

  return (
    <div className="space-y-6">
      <Card className="bg-card border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Risk Monitoring Parameters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3 flex-wrap">
            <div>
              <p className="text-xs text-muted-foreground mb-1">Lookback</p>
              <Select value={lookbackDays} onValueChange={setLookbackDays}>
                <SelectTrigger className="w-32 h-8 bg-muted/40 border-border text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="63">63D</SelectItem>
                  <SelectItem value="126">126D</SelectItem>
                  <SelectItem value="252">252D</SelectItem>
                  <SelectItem value="504">504D</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Frequency</p>
              <Select value={returnFrequency} onValueChange={(v: 'daily' | 'weekly') => setReturnFrequency(v)}>
                <SelectTrigger className="w-32 h-8 bg-muted/40 border-border text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="daily">Daily</SelectItem>
                  <SelectItem value="weekly">Weekly</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Confidence</p>
              <Select value={confidenceLevel} onValueChange={setConfidenceLevel}>
                <SelectTrigger className="w-32 h-8 bg-muted/40 border-border text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="0.9">90%</SelectItem>
                  <SelectItem value="0.95">95%</SelectItem>
                  <SelectItem value="0.99">99%</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Base Currency</p>
              <Select value={baseCurrency} onValueChange={setBaseCurrency}>
                <SelectTrigger className="w-32 h-8 bg-muted/40 border-border text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="USD">USD</SelectItem>
                  <SelectItem value="JPY">JPY</SelectItem>
                  <SelectItem value="EUR">EUR</SelectItem>
                  <SelectItem value="HKD">HKD</SelectItem>
                  <SelectItem value="CNY">CNY</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          {risk?.data_range?.start && risk?.data_range?.end && (
            <p className="text-xs text-muted-foreground mt-3">
              Base currency: {risk.base_currency ?? baseCurrency}.
              {' '}
              Data window: {risk.data_range.start} to {risk.data_range.end}
              {' '}
              ({risk.data_range.observations ?? 0} obs)
            </p>
          )}
          {risk?.fx_used && Object.keys(risk.fx_used).length > 0 && (
            <p className="text-xs text-muted-foreground mt-1">
              FX sources:
              {' '}
              {Object.entries(risk.fx_used).map(([ccy, t]) => `${ccy} via ${t}`).join(' | ')}
            </p>
          )}
          {!!risk?.warnings?.length && (
            <div className="mt-2 space-y-1">
              {risk.warnings.map((w) => (
                <p key={w} className="text-xs text-amber-500">{w}</p>
              ))}
            </div>
          )}
          <p className="text-[11px] text-muted-foreground mt-2">
            VaR / ES are per-period tail loss ({risk?.config_used?.return_frequency ?? returnFrequency}),
            while Volatility is annualized.
          </p>
        </CardContent>
      </Card>

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

      {risk?.risk_explainability && (
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="text-sm">Risk Change Explainability</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-4 gap-3">
              <div className="rounded border border-border bg-muted/40 p-3">
                <p className="text-xs text-muted-foreground">Total Delta Vol</p>
                <p className="text-sm font-semibold">{(risk.risk_explainability.total_delta_volatility * 100).toFixed(2)}%</p>
              </div>
              <div className="rounded border border-border bg-muted/40 p-3">
                <p className="text-xs text-muted-foreground">Weight Effect</p>
                <p className="text-sm font-semibold">{(risk.risk_explainability.weight_effect * 100).toFixed(2)}%</p>
              </div>
              <div className="rounded border border-border bg-muted/40 p-3">
                <p className="text-xs text-muted-foreground">Market Effect</p>
                <p className="text-sm font-semibold">{(risk.risk_explainability.market_effect * 100).toFixed(2)}%</p>
              </div>
              <div className="rounded border border-border bg-muted/40 p-3">
                <p className="text-xs text-muted-foreground">Interaction</p>
                <p className="text-sm font-semibold">{(risk.risk_explainability.interaction_effect * 100).toFixed(2)}%</p>
              </div>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-2">Top Risk Contributors</p>
              <div className="flex flex-wrap gap-2">
                {risk.risk_explainability.top_contributors.map((x) => (
                  <span key={x.ticker} className="text-xs px-2 py-1 rounded bg-muted/40 border border-border">
                    {x.ticker}: {(x.trc * 100).toFixed(2)}%
                  </span>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

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

