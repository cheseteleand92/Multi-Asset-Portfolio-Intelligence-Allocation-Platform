import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { ResponsiveContainer, Tooltip, LineChart, Line, XAxis, YAxis, CartesianGrid, PieChart, Pie, Cell } from 'recharts'
import { analyticsApi, portfolioApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'
import WhatIfDrawer from '@/components/WhatIfDrawer'

interface Position {
  id: number
  ticker: string
  asset_class: string
  quantity: number
  cost_price: number
  currency: string
}

interface Analytics {
  total_return?: number
  sharpe?: number
  nav?: Record<string, number>
  asset_nav?: Record<string, Record<string, number>>
  base_currency?: string
  fx_used?: Record<string, string>
  position_values_base?: Record<string, number>
  position_valuation?: Array<{
    position_id?: number | null
    ticker: string
    quantity: number
    currency: string
    base_currency: string
    price_local: number
    price_date?: string | null
    fx_rate_local_to_base: number
    fx_ticker?: string | null
    fx_date?: string | null
    value_local: number
    value_base: number
  }>
  allocation?: Array<{
    ticker: string
    value_base: number
    weight: number
  }>
  config_used?: {
    lookback_days: number
    return_frequency: string
  }
  data_range?: {
    start?: string | null
    end?: string | null
    observations?: number
  }
  warnings?: string[]
}

export default function PortfolioPage() {
  const { selectedPortfolioId } = useAppStore()
  const [whatIfOpen, setWhatIfOpen] = useState(false)
  const [lookbackDays, setLookbackDays] = useState('252')
  const [returnFrequency, setReturnFrequency] = useState<'daily' | 'weekly'>('daily')
  const [baseCurrency, setBaseCurrency] = useState('USD')
  const [cumTargetId, setCumTargetId] = useState<string>('portfolio')
  const [showInspector, setShowInspector] = useState(false)

  const { data: analytics, isLoading: analyticsLoading, isError: analyticsError } = useQuery<Analytics>({
    queryKey: ['analytics', selectedPortfolioId, lookbackDays, returnFrequency, baseCurrency],
    queryFn: () =>
      analyticsApi.getAnalytics(selectedPortfolioId!, {
        lookback_days: Number(lookbackDays),
        return_frequency: returnFrequency,
        base_currency: baseCurrency,
      }),
    enabled: !!selectedPortfolioId,
  })

  const { data: positions = [] } = useQuery<Position[]>({
    queryKey: ['positions', selectedPortfolioId],
    queryFn: () => portfolioApi.getPositions(selectedPortfolioId!),
    enabled: !!selectedPortfolioId,
  })

  const assetSeriesKeys = useMemo(() => Object.keys(analytics?.asset_nav ?? {}), [analytics?.asset_nav])
  const seriesOptions = useMemo(() => {
    const items = [{ id: 'portfolio', label: 'Portfolio', ticker: 'portfolio' }]
    for (const ticker of assetSeriesKeys) {
      items.push({ id: `asset:${encodeURIComponent(ticker)}`, label: ticker, ticker })
    }
    return items
  }, [assetSeriesKeys])
  const selectedSeries = seriesOptions.find((x) => x.id === cumTargetId) ?? seriesOptions[0]
  const selectedSeriesId = selectedSeries?.id ?? 'portfolio'
  const quantityByTicker = useMemo(() => {
    return positions.reduce<Record<string, number>>((acc, p) => {
      acc[p.ticker] = (acc[p.ticker] ?? 0) + p.quantity
      return acc
    }, {})
  }, [positions])
  const valuationByPositionId = useMemo(() => {
    const map: Record<number, NonNullable<Analytics['position_valuation']>[number]> = {}
    for (const row of analytics?.position_valuation ?? []) {
      if (row.position_id != null) map[row.position_id] = row
    }
    return map
  }, [analytics?.position_valuation])

  if (!selectedPortfolioId) {
    return <div className="text-muted-foreground text-sm">Select a portfolio from the header to begin.</div>
  }

  const totalReturn = analytics?.total_return
  const sharpe = analytics?.sharpe
  const allocationData = (analytics?.allocation ?? [])
    .filter((x) => x.value_base > 0)
    .map((x) => ({ name: x.ticker, size: x.value_base, weightPct: x.weight * 100 }))
  const totalValue = allocationData.reduce((acc, row) => acc + row.size, 0)
  const allocationColors = ['#0ea5e9', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#14b8a6', '#64748b']
  const allocationColorByName: Record<string, string> = {}
  allocationData.forEach((row, idx) => {
    allocationColorByName[row.name] = allocationColors[idx % allocationColors.length]
  })

  const cumulativeChartData = (() => {
    const source =
      selectedSeries.ticker === 'portfolio'
        ? analytics?.nav
        : analytics?.asset_nav?.[selectedSeries.ticker]
    if (!source) return []
    return Object.entries(source)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, nav]) => ({ date, cumret: (nav - 1) * 100 }))
  })()
  const inspectorSummary = {
    base_currency: analytics?.base_currency ?? null,
    positions_count: positions.length,
    nav_points: Object.keys(analytics?.nav ?? {}).length,
    asset_series_count: Object.keys(analytics?.asset_nav ?? {}).length,
    value_series_count: Object.keys(analytics?.position_values_base ?? {}).length,
    position_valuation_count: analytics?.position_valuation?.length ?? 0,
    fx_used_count: Object.keys(analytics?.fx_used ?? {}).length,
    warnings_count: analytics?.warnings?.length ?? 0,
  }

  return (
    <div className="space-y-6">
      <Card className="bg-card border-border">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Monitoring Parameters</CardTitle>
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs border-border bg-muted/40"
              onClick={() => setShowInspector((s) => !s)}
            >
              {showInspector ? 'Hide Inspector' : 'Show Inspector'}
            </Button>
          </div>
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
          {analytics?.data_range?.start && analytics?.data_range?.end && (
            <p className="text-xs text-muted-foreground mt-3">
              Base currency: {analytics.base_currency ?? 'USD'}.
              {' '}
              Data window: {analytics.data_range.start} to {analytics.data_range.end}
              {' '}
              ({analytics.data_range.observations ?? 0} obs)
            </p>
          )}
          {analytics?.fx_used && Object.keys(analytics.fx_used).length > 0 && (
            <p className="text-xs text-muted-foreground mt-1">
              FX sources:
              {' '}
              {Object.entries(analytics.fx_used).map(([ccy, t]) => `${ccy} via ${t}`).join(' | ')}
            </p>
          )}
          {!!analytics?.warnings?.length && (
            <div className="mt-2 space-y-1">
              {analytics.warnings.map((w) => (
                <p key={w} className="text-xs text-amber-500">{w}</p>
              ))}
            </div>
          )}
          {analyticsError && (
            <p className="text-xs text-destructive mt-2">Failed to load monitoring analytics data.</p>
          )}
          {showInspector && (
            <div className="mt-4 space-y-2">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {Object.entries(inspectorSummary).map(([k, v]) => (
                  <div key={k} className="rounded border border-border bg-muted/30 px-2 py-1">
                    <p className="text-[10px] text-muted-foreground">{k}</p>
                    <p className="text-xs font-mono">{String(v)}</p>
                  </div>
                ))}
              </div>
              <details className="rounded border border-border bg-muted/20 px-2 py-2">
                <summary className="text-xs cursor-pointer text-muted-foreground">Raw Monitoring Payload</summary>
                <pre className="text-[10px] leading-4 overflow-auto max-h-64 mt-2">
                  {JSON.stringify(analytics ?? {}, null, 2)}
                </pre>
              </details>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-3 gap-4">
        <Card className="bg-card border-border">
          <CardHeader className="pb-1">
            <CardTitle className="text-xs text-muted-foreground">Total Return</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-2xl font-bold ${(totalReturn ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {totalReturn != null ? `${(totalReturn * 100).toFixed(2)}%` : '—'}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-card border-border">
          <CardHeader className="pb-1">
            <CardTitle className="text-xs text-muted-foreground">Sharpe Ratio</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{sharpe != null ? sharpe.toFixed(2) : '—'}</p>
          </CardContent>
        </Card>
        <Card className="bg-card border-border">
          <CardHeader className="pb-1">
            <CardTitle className="text-xs text-muted-foreground">Positions</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{positions.length}</p>
          </CardContent>
        </Card>
      </div>

      <Card className="bg-card border-border">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-sm">Cumulative Return</CardTitle>
          <Select value={selectedSeriesId} onValueChange={setCumTargetId}>
            <SelectTrigger className="w-52 h-8 bg-muted/40 border-border text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {seriesOptions.map((opt) => (
                <SelectItem key={opt.id} value={opt.id}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardHeader>
        <CardContent>
          {cumulativeChartData.length === 0 ? (
            <p className="text-xs text-muted-foreground">No cumulative return series for selected target.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={cumulativeChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#94a3b8" strokeOpacity={0.3} />
                <XAxis dataKey="date" tickFormatter={(v: string) => v.slice(2, 10)} tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={(v: number) => `${v.toFixed(1)}%`} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => `${v.toFixed(2)}%`} />
                <Line type="monotone" dataKey="cumret" stroke="#0ea5e9" strokeWidth={2.2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <Card className="bg-card border-border">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-sm">Allocation</CardTitle>
          <Button
            size="sm"
            variant="outline"
            className="border-border bg-muted/40 text-xs h-7"
            onClick={() => setWhatIfOpen(true)}
          >
            What-if
          </Button>
        </CardHeader>
        <CardContent>
          {analyticsLoading ? (
            <p className="text-xs text-muted-foreground">Loading allocation...</p>
          ) : totalValue <= 0 ? (
            <p className="text-xs text-muted-foreground">No allocation value available for current holdings.</p>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={allocationData} dataKey="size" nameKey="name" innerRadius={46} outerRadius={84} paddingAngle={2}>
                    {allocationData.map((entry, idx) => (
                      <Cell key={`${entry.name}-${idx}`} fill={allocationColorByName[entry.name] ?? allocationColors[idx % allocationColors.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(v: unknown, _name: string, item: { payload?: { weightPct?: number } }) => {
                      const pct = item.payload?.weightPct ?? 0
                      return [
                        `${analytics?.base_currency ?? 'USD'} ${(v as number).toLocaleString()} (${pct.toFixed(2)}%)`,
                        'Value',
                      ]
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-1 overflow-auto max-h-[220px] pr-1">
                {allocationData
                  .slice()
                  .sort((a, b) => b.size - a.size)
                  .map((row, idx) => (
                    <div key={row.name} className="flex items-center justify-between text-xs">
                      <span className="truncate pr-2" title={row.name}>
                        <span
                          className="inline-block w-2 h-2 rounded-full mr-2 align-middle"
                          style={{ backgroundColor: allocationColorByName[row.name] ?? allocationColors[idx % allocationColors.length] }}
                        />
                        {row.name}
                      </span>
                      <span className="text-muted-foreground">
                        {row.weightPct.toFixed(1)}%
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="text-sm">Positions Snapshot</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="border-border">
                <TableHead className="text-muted-foreground text-xs">Ticker</TableHead>
                <TableHead className="text-muted-foreground text-xs">Asset Class</TableHead>
                <TableHead className="text-muted-foreground text-xs text-right">Quantity</TableHead>
                <TableHead className="text-muted-foreground text-xs text-right">Cost Price</TableHead>
                <TableHead className="text-muted-foreground text-xs text-right">Value</TableHead>
                <TableHead className="text-muted-foreground text-xs">Currency</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {positions.map((p) => (
                <TableRow key={p.id} className="border-border hover:bg-accent/60">
                  <TableCell className="text-xs font-mono">{p.ticker}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{p.asset_class}</TableCell>
                  <TableCell className="text-xs text-right">{p.quantity.toLocaleString()}</TableCell>
                  <TableCell className="text-xs text-right">${p.cost_price.toFixed(2)}</TableCell>
                  <TableCell className="text-xs text-right font-medium">
                    {analyticsLoading
                      ? 'Loading...'
                      : valuationByPositionId[p.id] != null
                      ? (() => {
                          const valuation = valuationByPositionId[p.id]
                          return `${valuation.base_currency ?? analytics?.base_currency ?? 'USD'} ${valuation.value_base.toLocaleString()}`
                        })()
                      : analytics?.position_values_base?.[p.ticker] != null
                      ? (() => {
                          const tickerValue = analytics.position_values_base?.[p.ticker] ?? 0
                          const tickerQty = quantityByTicker[p.ticker] ?? 0
                          const positionValue = tickerQty > 0 ? (tickerValue * p.quantity) / tickerQty : tickerValue
                          return `${analytics.base_currency ?? 'USD'} ${positionValue.toLocaleString()}`
                        })()
                      : `${p.currency} ${(p.quantity * p.cost_price).toLocaleString()} (cost)`}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">{p.currency}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <WhatIfDrawer
        open={whatIfOpen}
        onClose={() => setWhatIfOpen(false)}
        positions={positions}
        portfolioId={selectedPortfolioId}
      />
    </div>
  )
}
