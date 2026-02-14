import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle } from '@/components/ui/drawer'
import { Slider } from '@/components/ui/slider'
import { Button } from '@/components/ui/button'
import { analyticsApi } from '@/lib/api'

interface Position {
  id: number
  ticker: string
  quantity: number
  cost_price: number
}

interface Props {
  open: boolean
  onClose: () => void
  positions: Position[]
  portfolioId: number
}

export default function WhatIfDrawer({ open, onClose, positions, portfolioId }: Props) {
  const totalValue = positions.reduce((s, p) => s + p.quantity * p.cost_price, 0)
  const initWeights: Record<string, number> = Object.fromEntries(
    positions.map((p) => [p.ticker, totalValue > 0 ? (p.quantity * p.cost_price) / totalValue : 0])
  )
  const [weights, setWeights] = useState<Record<string, number>>(initWeights)
  const [result, setResult] = useState<{ var_95: number; volatility: number } | null>(null)

  const whatIf = useMutation({
    mutationFn: () => analyticsApi.whatIf(portfolioId, weights),
    onSuccess: (data) => setResult(data as { var_95: number; volatility: number }),
  })

  return (
    <Drawer open={open} onClose={onClose} direction="right">
      <DrawerContent className="bg-card border-border w-80 right-0 left-auto top-0 bottom-0 fixed mt-0 rounded-none">
        <DrawerHeader>
          <DrawerTitle className="text-sm">What-if Sandbox</DrawerTitle>
        </DrawerHeader>
        <div className="px-4 pb-4 space-y-4 overflow-y-auto">
          {positions.map((p) => (
            <div key={p.ticker}>
              <div className="flex justify-between text-xs text-muted-foreground mb-1">
                <span className="font-mono">{p.ticker}</span>
                <span>{((weights[p.ticker] ?? 0) * 100).toFixed(1)}%</span>
              </div>
              <Slider
                min={0}
                max={1}
                step={0.01}
                value={[weights[p.ticker] ?? 0]}
                onValueChange={([v]) => setWeights((w) => ({ ...w, [p.ticker]: v }))}
              />
            </div>
          ))}

          <Button
            size="sm"
            className="w-full"
            onClick={() => whatIf.mutate()}
            disabled={whatIf.isPending}
          >
            Calculate Impact
          </Button>

          {result && (
            <div className="space-y-2 pt-2 border-t border-border">
              <p className="text-xs text-muted-foreground">Results</p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-muted/40 rounded p-2">
                  <p className="text-muted-foreground">VaR 95%</p>
                  <p className="font-bold text-amber-400">{(result.var_95 * 100).toFixed(2)}%</p>
                </div>
                <div className="bg-muted/40 rounded p-2">
                  <p className="text-muted-foreground">Volatility</p>
                  <p className="font-bold">{(result.volatility * 100).toFixed(2)}%</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </DrawerContent>
    </Drawer>
  )
}

