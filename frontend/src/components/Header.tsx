import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Moon, RefreshCw, Sun } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { portfolioApi, marketApi, signalsApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'

export default function Header() {
  const qc = useQueryClient()
  const { selectedPortfolioId, setSelectedPortfolio, setOnline, theme, toggleTheme } = useAppStore()
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
    <header className="flex items-center justify-between px-6 py-3 bg-card/95 border-b border-border backdrop-blur">
      <div className="flex items-center gap-4">
        <span className="font-semibold text-sm text-muted-foreground">Portfolio</span>
        <Select
          value={String(selectedPortfolioId ?? '')}
          onValueChange={(v) => setSelectedPortfolio(Number(v))}
        >
          <SelectTrigger className="w-48 h-8 bg-muted/40 border-border text-sm">
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
              className="h-8 w-44 rounded-md border border-border bg-muted/40 px-2 text-xs text-foreground"
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
              className="h-8 text-xs border-border bg-muted/40"
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
            className="h-8 text-xs border-border bg-muted/40"
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
          className="h-8 text-xs border-border bg-muted/40"
          onClick={() => refresh.mutate()}
          disabled={refresh.isPending}
        >
          <RefreshCw size={14} className={refresh.isPending ? 'animate-spin mr-1' : 'mr-1'} />
          Refresh Data
        </Button>
        <Button
          size="icon"
          variant="outline"
          className="h-8 w-8 border-border bg-muted/40"
          onClick={toggleTheme}
          title={theme === 'dark' ? 'Switch to day mode' : 'Switch to night mode'}
        >
          {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
        </Button>
      </div>
    </header>
  )
}

