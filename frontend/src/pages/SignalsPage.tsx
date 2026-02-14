import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { signalsApi } from '@/lib/api'

interface SignalData {
  momentum: number
  mean_reversion: number
  vol_breakout: number
}

function SignalCell({ value }: { value: number }) {
  const isNaN_ = Number.isNaN(value)
  const color = isNaN_ ? 'text-zinc-500' : value > 0 ? 'text-emerald-400' : 'text-red-400'
  return (
    <TableCell className={`text-xs text-right font-mono ${color}`}>
      {isNaN_ ? '—' : value.toFixed(4)}
    </TableCell>
  )
}

export default function SignalsPage() {
  const { data: regime } = useQuery({ queryKey: ['regime'], queryFn: signalsApi.getRegime })
  const { data: signals } = useQuery<Record<string, SignalData>>({
    queryKey: ['signals'],
    queryFn: signalsApi.getSignals,
  })

  const entries = signals ? Object.entries(signals) : []

  return (
    <div className="space-y-6">
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-sm">Market Regime</CardTitle>
        </CardHeader>
        <CardContent>
          {regime ? (
            <Badge
              variant={regime.regime === 'risk_on' ? 'default' : 'destructive'}
              className="text-sm px-3 py-1"
            >
              {regime.regime === 'risk_on' ? '● Risk-On' : '● Risk-Off'}
            </Badge>
          ) : (
            <span className="text-zinc-500 text-sm">Loading…</span>
          )}
        </CardContent>
      </Card>

      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-sm">Alpha Signals by Ticker</CardTitle>
        </CardHeader>
        <CardContent>
          {entries.length === 0 ? (
            <p className="text-zinc-500 text-sm">
              No signals available — add positions and refresh market data first.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-zinc-800">
                  <TableHead className="text-zinc-400 text-xs">Ticker</TableHead>
                  <TableHead className="text-zinc-400 text-xs text-right">Momentum</TableHead>
                  <TableHead className="text-zinc-400 text-xs text-right">Mean Reversion</TableHead>
                  <TableHead className="text-zinc-400 text-xs text-right">Vol Breakout</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {entries.map(([ticker, s]) => (
                  <TableRow key={ticker} className="border-zinc-800 hover:bg-zinc-800/50">
                    <TableCell className="text-xs font-mono">{ticker}</TableCell>
                    <SignalCell value={s.momentum} />
                    <SignalCell value={s.mean_reversion} />
                    <SignalCell value={s.vol_breakout} />
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
