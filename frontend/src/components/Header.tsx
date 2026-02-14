import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { portfolioApi, marketApi, signalsApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'

export default function Header() {
  const qc = useQueryClient()
  const { selectedPortfolioId, setSelectedPortfolio, setOnline } = useAppStore()
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const { data: portfolios = [] } = useQuery({ queryKey: ['portfolios'], queryFn: portfolioApi.list })
  const { data: regime } = useQuery({
    queryKey: ['regime'],
    queryFn: signalsApi.getRegime,
    refetchInterval: 60000,
  })

  const refresh = useMutation({
    mutationFn: marketApi.refresh,
    onSuccess: (data: { online: boolean }) => setOnline(data.online),
  })

  const createPortfolio = useMutation({
    mutationFn: (name: string) => portfolioApi.create({ name }),
    onSuccess: (data: { id: number }) => {
      setNewName('')
      setCreating(false)
      setSelectedPortfolio(data.id)
      void qc.invalidateQueries({ queryKey: ['portfolios'] })
    },
  })

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-zinc-900 border-b border-zinc-800">
      <div className="flex items-center gap-4">
        <span className="font-semibold text-sm text-zinc-300">Portfolio</span>
        <Select
          value={String(selectedPortfolioId ?? '')}
          onValueChange={(v) => setSelectedPortfolio(Number(v))}
        >
          <SelectTrigger className="w-48 h-8 bg-zinc-800 border-zinc-700 text-sm">
            <SelectValue placeholder="Select portfolio" />
          </SelectTrigger>
          <SelectContent>
            {(portfolios as { id: number; name: string }[]).map((p) => (
              <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {creating ? (
          <div className="flex items-center gap-2">
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="New portfolio name"
              className="h-8 w-44 rounded-md border border-zinc-700 bg-zinc-800 px-2 text-xs text-zinc-100"
            />
            <Button
              size="sm"
              className="h-8 text-xs"
              onClick={() => createPortfolio.mutate(newName.trim())}
              disabled={!newName.trim() || createPortfolio.isPending}
            >
              Create
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-8 text-xs border-zinc-700 bg-zinc-800"
              onClick={() => {
                setCreating(false)
                setNewName('')
              }}
            >
              Cancel
            </Button>
          </div>
        ) : (
          <Button
            size="sm"
            variant="outline"
            className="h-8 text-xs border-zinc-700 bg-zinc-800"
            onClick={() => setCreating(true)}
          >
            New Portfolio
          </Button>
        )}
      </div>
      <div className="flex items-center gap-3">
        {regime && (
          <Badge
            variant={regime.regime === 'risk_on' ? 'default' : 'destructive'}
            className="text-xs"
          >
            {regime.regime === 'risk_on' ? '● Risk-On' : '● Risk-Off'}
          </Badge>
        )}
        <Button
          size="sm"
          variant="outline"
          className="h-8 text-xs border-zinc-700 bg-zinc-800"
          onClick={() => refresh.mutate()}
          disabled={refresh.isPending}
        >
          <RefreshCw size={14} className={refresh.isPending ? 'animate-spin mr-1' : 'mr-1'} />
          Refresh Data
        </Button>
      </div>
    </header>
  )
}
