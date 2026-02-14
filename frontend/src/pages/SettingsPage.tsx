import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { marketApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'

const CSV_TEMPLATE = 'ticker,quantity,cost_price,currency,asset_class\n'

function downloadCsvTemplate() {
  const blob = new Blob([CSV_TEMPLATE], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'holdings_template.csv'
  a.click()
  URL.revokeObjectURL(url)
}

export default function SettingsPage() {
  const { isOnline } = useAppStore()

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => fetch('/api/health').then((r) => r.json()),
    refetchInterval: 30000,
  })

  const { data: refreshStatus } = useQuery({
    queryKey: ['refresh-status'],
    queryFn: marketApi.refresh,
    enabled: false,
  })

  return (
    <div className="space-y-6 max-w-xl">
      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="text-sm">System Status</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">API Server</span>
            <Badge variant={health?.status === 'ok' ? 'default' : 'destructive'} className="text-xs">
              {health?.status === 'ok' ? '● Online' : '● Offline'}
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Bloomberg</span>
            <Badge variant={isOnline ? 'default' : 'secondary'} className="text-xs">
              {isOnline ? '● Connected' : '● Offline (cached data)'}
            </Badge>
          </div>
          {refreshStatus && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Last refresh</span>
              <span className="text-xs text-foreground/80">
                {refreshStatus.refreshed_rows} rows across {refreshStatus.tickers} tickers
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="text-sm">CSV Import</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-muted-foreground">
            Import holdings via CSV on the Portfolio page. Required columns:
          </p>
          <code className="block text-xs bg-muted/40 rounded p-3 text-foreground/80 font-mono">
            {CSV_TEMPLATE.trim()}
          </code>
          <Button
            size="sm"
            variant="outline"
            className="border-border bg-muted/40 text-xs"
            onClick={downloadCsvTemplate}
          >
            Download CSV Template
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

