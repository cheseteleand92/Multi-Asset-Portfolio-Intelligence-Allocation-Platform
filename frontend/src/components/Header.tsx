import { useQuery, useMutation } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { portfolioApi, marketApi, signalsApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'

export default function Header() {
  const { selectedPortfolioId, setSelectedPortfolio, setOnline } = useAppStore()
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
