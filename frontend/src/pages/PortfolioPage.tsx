import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Treemap, ResponsiveContainer, Tooltip } from 'recharts'
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
}

export default function PortfolioPage() {
  const { selectedPortfolioId } = useAppStore()
  const [whatIfOpen, setWhatIfOpen] = useState(false)

  const { data: analytics } = useQuery<Analytics>({
    queryKey: ['analytics', selectedPortfolioId],
    queryFn: () => analyticsApi.getAnalytics(selectedPortfolioId!),
    enabled: !!selectedPortfolioId,
  })

  const { data: positions = [] } = useQuery<Position[]>({
    queryKey: ['positions', selectedPortfolioId],
    queryFn: () => portfolioApi.getPositions(selectedPortfolioId!),
    enabled: !!selectedPortfolioId,
  })

  if (!selectedPortfolioId) {
    return <div className="text-zinc-500 text-sm">Select a portfolio from the header to begin.</div>
  }

  const totalReturn = analytics?.total_return
  const sharpe = analytics?.sharpe
  const treemapData = positions.map((p) => ({
    name: p.ticker,
    size: p.quantity * p.cost_price,
  }))

  return (
    <div className="space-y-6">
      {/* Metric cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-1">
            <CardTitle className="text-xs text-zinc-400">Total Return</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-2xl font-bold ${(totalReturn ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {totalReturn != null ? `${(totalReturn * 100).toFixed(2)}%` : '—'}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-1">
            <CardTitle className="text-xs text-zinc-400">Sharpe Ratio</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{sharpe != null ? sharpe.toFixed(2) : '—'}</p>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-1">
            <CardTitle className="text-xs text-zinc-400">Positions</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{positions.length}</p>
          </CardContent>
        </Card>
      </div>

      {/* Treemap */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-sm">Allocation</CardTitle>
          <Button
            size="sm"
            variant="outline"
            className="border-zinc-700 bg-zinc-800 text-xs h-7"
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

      {/* Positions table */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-sm">Positions</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="border-zinc-800">
                <TableHead className="text-zinc-400 text-xs">Ticker</TableHead>
                <TableHead className="text-zinc-400 text-xs">Asset Class</TableHead>
                <TableHead className="text-zinc-400 text-xs text-right">Quantity</TableHead>
                <TableHead className="text-zinc-400 text-xs text-right">Cost Price</TableHead>
                <TableHead className="text-zinc-400 text-xs text-right">Value</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {positions.map((p) => (
                <TableRow key={p.id} className="border-zinc-800 hover:bg-zinc-800/50">
                  <TableCell className="text-xs font-mono">{p.ticker}</TableCell>
                  <TableCell className="text-xs text-zinc-400">{p.asset_class}</TableCell>
                  <TableCell className="text-xs text-right">{p.quantity.toLocaleString()}</TableCell>
                  <TableCell className="text-xs text-right">${p.cost_price.toFixed(2)}</TableCell>
                  <TableCell className="text-xs text-right font-medium">
                    ${(p.quantity * p.cost_price).toLocaleString()}
                  </TableCell>
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
