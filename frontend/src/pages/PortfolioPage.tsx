import { useQuery } from '@tanstack/react-query'
import { useMutation, useQueryClient } from '@tanstack/react-query'
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

interface PositionForm {
  ticker: string
  asset_class: string
  quantity: string
  cost_price: string
  currency: string
}

interface Analytics {
  total_return?: number
  sharpe?: number
}

const EMPTY_FORM: PositionForm = {
  ticker: '',
  asset_class: 'Equity',
  quantity: '',
  cost_price: '',
  currency: 'USD',
}

function isValidPositionForm(form: PositionForm): boolean {
  if (form.quantity.trim().length === 0 || form.cost_price.trim().length === 0) {
    return false
  }
  const quantity = Number(form.quantity)
  const costPrice = Number(form.cost_price)
  return (
    form.ticker.trim().length > 0 &&
    form.asset_class.trim().length > 0 &&
    form.currency.trim().length > 0 &&
    Number.isFinite(quantity) &&
    Number.isFinite(costPrice)
  )
}

function toPositionPayload(form: PositionForm) {
  return {
    ticker: form.ticker.trim(),
    asset_class: form.asset_class.trim(),
    quantity: Number(form.quantity),
    cost_price: Number(form.cost_price),
    currency: form.currency.trim().toUpperCase(),
  }
}

export default function PortfolioPage() {
  const { selectedPortfolioId } = useAppStore()
  const qc = useQueryClient()
  const [whatIfOpen, setWhatIfOpen] = useState(false)
  const [newPosition, setNewPosition] = useState<PositionForm>(EMPTY_FORM)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editingForm, setEditingForm] = useState<PositionForm>(EMPTY_FORM)
  const [csvFile, setCsvFile] = useState<File | null>(null)
  const [replaceOnImport, setReplaceOnImport] = useState(false)
  const [status, setStatus] = useState<string | null>(null)

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

  const refreshPortfolioData = async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ['positions', selectedPortfolioId] }),
      qc.invalidateQueries({ queryKey: ['analytics', selectedPortfolioId] }),
      qc.invalidateQueries({ queryKey: ['risk', selectedPortfolioId] }),
      qc.invalidateQueries({ queryKey: ['signals'] }),
    ])
  }

  const addPosition = useMutation({
    mutationFn: () => portfolioApi.addPosition(selectedPortfolioId!, toPositionPayload(newPosition)),
    onSuccess: async () => {
      setStatus('Position added.')
      setNewPosition(EMPTY_FORM)
      await refreshPortfolioData()
    },
  })

  const updatePosition = useMutation({
    mutationFn: () => portfolioApi.updatePosition(editingId!, toPositionPayload(editingForm)),
    onSuccess: async () => {
      setStatus('Position updated.')
      setEditingId(null)
      await refreshPortfolioData()
    },
  })

  const deletePosition = useMutation({
    mutationFn: (id: number) => portfolioApi.deletePosition(id),
    onSuccess: async () => {
      setStatus('Position deleted.')
      await refreshPortfolioData()
    },
  })

  const importCsv = useMutation({
    mutationFn: () => portfolioApi.importCsv(selectedPortfolioId!, csvFile!, replaceOnImport),
    onSuccess: async (data: { imported: number }) => {
      setStatus(`CSV imported: ${data.imported} rows.`)
      setCsvFile(null)
      await refreshPortfolioData()
    },
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
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-sm">Manage Holdings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-6 gap-2">
            <input
              value={newPosition.ticker}
              onChange={(e) => setNewPosition((s) => ({ ...s, ticker: e.target.value }))}
              placeholder="Ticker"
              className="h-8 rounded border border-zinc-700 bg-zinc-800 px-2 text-xs text-zinc-100"
            />
            <input
              value={newPosition.asset_class}
              onChange={(e) => setNewPosition((s) => ({ ...s, asset_class: e.target.value }))}
              placeholder="Asset Class"
              className="h-8 rounded border border-zinc-700 bg-zinc-800 px-2 text-xs text-zinc-100"
            />
            <input
              type="number"
              value={newPosition.quantity}
              onChange={(e) => setNewPosition((s) => ({ ...s, quantity: e.target.value }))}
              placeholder="Quantity"
              className="h-8 rounded border border-zinc-700 bg-zinc-800 px-2 text-xs text-zinc-100"
            />
            <input
              type="number"
              value={newPosition.cost_price}
              onChange={(e) => setNewPosition((s) => ({ ...s, cost_price: e.target.value }))}
              placeholder="Cost Price"
              className="h-8 rounded border border-zinc-700 bg-zinc-800 px-2 text-xs text-zinc-100"
            />
            <input
              value={newPosition.currency}
              onChange={(e) => setNewPosition((s) => ({ ...s, currency: e.target.value }))}
              placeholder="Currency"
              className="h-8 rounded border border-zinc-700 bg-zinc-800 px-2 text-xs text-zinc-100"
            />
            <Button
              size="sm"
              className="h-8 text-xs"
              onClick={() => addPosition.mutate()}
              disabled={!isValidPositionForm(newPosition) || addPosition.isPending}
            >
              Add Position
            </Button>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)}
              className="text-xs text-zinc-300 file:mr-3 file:rounded file:border-0 file:bg-zinc-800 file:px-2 file:py-1 file:text-zinc-100"
            />
            <label className="flex items-center gap-2 text-xs text-zinc-400">
              <input
                type="checkbox"
                checked={replaceOnImport}
                onChange={(e) => setReplaceOnImport(e.target.checked)}
              />
              Replace existing positions
            </label>
            <Button
              size="sm"
              variant="outline"
              className="h-8 text-xs border-zinc-700 bg-zinc-800"
              onClick={() => importCsv.mutate()}
              disabled={!csvFile || importCsv.isPending}
            >
              Upload CSV
            </Button>
          </div>

          {status && <p className="text-xs text-emerald-400">{status}</p>}
        </CardContent>
      </Card>

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
                <TableHead className="text-zinc-400 text-xs">Currency</TableHead>
                <TableHead className="text-zinc-400 text-xs text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {positions.map((p) => (
                <TableRow key={p.id} className="border-zinc-800 hover:bg-zinc-800/50">
                  {editingId === p.id ? (
                    <>
                      <TableCell className="py-2">
                        <input
                          value={editingForm.ticker}
                          onChange={(e) => setEditingForm((s) => ({ ...s, ticker: e.target.value }))}
                          className="h-8 w-36 rounded border border-zinc-700 bg-zinc-800 px-2 text-xs text-zinc-100"
                        />
                      </TableCell>
                      <TableCell className="py-2">
                        <input
                          value={editingForm.asset_class}
                          onChange={(e) => setEditingForm((s) => ({ ...s, asset_class: e.target.value }))}
                          className="h-8 w-28 rounded border border-zinc-700 bg-zinc-800 px-2 text-xs text-zinc-100"
                        />
                      </TableCell>
                      <TableCell className="py-2 text-right">
                        <input
                          type="number"
                          value={editingForm.quantity}
                          onChange={(e) => setEditingForm((s) => ({ ...s, quantity: e.target.value }))}
                          className="h-8 w-24 rounded border border-zinc-700 bg-zinc-800 px-2 text-xs text-zinc-100"
                        />
                      </TableCell>
                      <TableCell className="py-2 text-right">
                        <input
                          type="number"
                          value={editingForm.cost_price}
                          onChange={(e) => setEditingForm((s) => ({ ...s, cost_price: e.target.value }))}
                          className="h-8 w-24 rounded border border-zinc-700 bg-zinc-800 px-2 text-xs text-zinc-100"
                        />
                      </TableCell>
                      <TableCell className="py-2 text-right">
                        <span className="text-xs text-zinc-400">Editing…</span>
                      </TableCell>
                      <TableCell className="py-2">
                        <input
                          value={editingForm.currency}
                          onChange={(e) => setEditingForm((s) => ({ ...s, currency: e.target.value }))}
                          className="h-8 w-20 rounded border border-zinc-700 bg-zinc-800 px-2 text-xs text-zinc-100"
                        />
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            size="sm"
                            className="h-7 text-xs"
                            onClick={() => updatePosition.mutate()}
                            disabled={!isValidPositionForm(editingForm) || updatePosition.isPending}
                          >
                            Save
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs border-zinc-700 bg-zinc-800"
                            onClick={() => setEditingId(null)}
                          >
                            Cancel
                          </Button>
                        </div>
                      </TableCell>
                    </>
                  ) : (
                    <>
                      <TableCell className="text-xs font-mono">{p.ticker}</TableCell>
                      <TableCell className="text-xs text-zinc-400">{p.asset_class}</TableCell>
                      <TableCell className="text-xs text-right">{p.quantity.toLocaleString()}</TableCell>
                      <TableCell className="text-xs text-right">${p.cost_price.toFixed(2)}</TableCell>
                      <TableCell className="text-xs text-right font-medium">
                        ${(p.quantity * p.cost_price).toLocaleString()}
                      </TableCell>
                      <TableCell className="text-xs text-zinc-400">{p.currency}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs border-zinc-700 bg-zinc-800"
                            onClick={() => {
                              setEditingId(p.id)
                              setEditingForm({
                                ticker: p.ticker,
                                asset_class: p.asset_class,
                                quantity: String(p.quantity),
                                cost_price: String(p.cost_price),
                                currency: p.currency,
                              })
                            }}
                          >
                            Edit
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs border-zinc-700 bg-zinc-800 text-red-300"
                            onClick={() => deletePosition.mutate(p.id)}
                            disabled={deletePosition.isPending}
                          >
                            Delete
                          </Button>
                        </div>
                      </TableCell>
                    </>
                  )}
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
