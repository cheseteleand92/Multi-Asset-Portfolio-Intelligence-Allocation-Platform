import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Treemap, ResponsiveContainer, Tooltip, LineChart, Line, XAxis, YAxis, CartesianGrid } from 'recharts'
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
  const [cumTarget, setCumTarget] = useState<string>('portfolio')

  const { data: analytics } = useQuery<Analytics>({
    queryKey: ['analytics', selectedPortfolioId, lookbackDays, returnFrequency],
    queryFn: () =>
      analyticsApi.getAnalytics(selectedPortfolioId!, {
        lookback_days: Number(lookbackDays),
        return_frequency: returnFrequency,
      }),
    enabled: !!selectedPortfolioId,
  })

  const { data: positions = [] } = useQuery<Position[]>({
    queryKey: ['positions', selectedPortfolioId],
    queryFn: () => portfolioApi.getPositions(selectedPortfolioId!),
    enabled: !!selectedPortfolioId,
  })

  if (!selectedPortfolioId) {
    return <div className="text-muted-foreground text-sm">Select a portfolio from the header to begin.</div>
  }

  const totalReturn = analytics?.total_return
  const sharpe = analytics?.sharpe
  const treemapData = positions.map((p) => ({
    name: p.ticker,
    size: p.quantity * p.cost_price,
  }))
  const cumulativeChartData = (() => {
    const source = cumTarget === 'portfolio' ? analytics?.nav : analytics?.asset_nav?.[cumTarget]
    if (!source) return []
    return Object.entries(source)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, nav]) => ({ date, cumret: (nav - 1) * 100 }))
  })()

  return (
    <div className="space-y-6">
      <Card className="bg-card border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Monitoring Parameters</CardTitle>
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
          <Select value={cumTarget} onValueChange={setCumTarget}>
            <SelectTrigger className="w-52 h-8 bg-muted/40 border-border text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="portfolio">Portfolio</SelectItem>
              {positions.map((p) => (
                <SelectItem key={p.ticker} value={p.ticker}>{p.ticker}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={cumulativeChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#94a3b8" strokeOpacity={0.3} />
              <XAxis dataKey="date" tickFormatter={(v: string) => v.slice(2, 10)} tick={{ fontSize: 11 }} />
              <YAxis tickFormatter={(v: number) => `${v.toFixed(1)}%`} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: number) => `${v.toFixed(2)}%`} />
              <Line type="monotone" dataKey="cumret" stroke="#0ea5e9" strokeWidth={2.2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
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
          <ResponsiveContainer width="100%" height={220}>
            <Treemap data={treemapData} dataKey="size" nameKey="name" stroke="#18181b" fill="#3f3f46">
              <Tooltip formatter={(v: unknown) => `$${(v as number).toLocaleString()}`} />
            </Treemap>
          </ResponsiveContainer>
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
                    ${(p.quantity * p.cost_price).toLocaleString()}
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
