import { cva, type VariantProps } from 'class-variance-authority'
import { TrendingDown, TrendingUp } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

const kpiCardVariants = cva('px-4 py-3', {
  variants: {
    layout: {
      inline: '',
      stacked: '',
    },
  },
  defaultVariants: { layout: 'stacked' },
})

export interface KpiCardProps extends VariantProps<typeof kpiCardVariants> {
  label: string
  value: string
  hint?: string
  trend?: { direction: 'up' | 'down'; label: string }
  isLoading?: boolean
  className?: string
}

export function KpiCard({ label, value, hint, trend, isLoading, layout, className }: KpiCardProps) {
  if (isLoading) {
    return (
      <Card className={cn(kpiCardVariants({ layout }), className)}>
        <Skeleton className="h-3 w-28" />
        <Skeleton className="mt-2 h-6 w-20" />
      </Card>
    )
  }

  const trendNode = trend ? (
    <span
      className={cn(
        'flex items-center gap-0.5 text-xs font-medium',
        trend.direction === 'up' ? 'text-success-600' : 'text-danger-600',
      )}
    >
      {trend.direction === 'up' ? (
        <TrendingUp className="size-3" />
      ) : (
        <TrendingDown className="size-3" />
      )}
      {trend.label}
    </span>
  ) : null

  if (layout === 'inline') {
    return (
      <Card className={cn(kpiCardVariants({ layout }), className)}>
        <div className="flex items-baseline justify-between gap-3">
          <span className="truncate text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </span>
          <span className="shrink-0 text-2xl font-semibold tabular-nums">{value}</span>
        </div>
        {(hint || trendNode) && (
          <div className="mt-0.5 flex items-center justify-between gap-2">
            {hint ? <span className="truncate text-xs text-muted-foreground">{hint}</span> : <span />}
            {trendNode}
          </div>
        )}
      </Card>
    )
  }

  return (
    <Card className={cn(kpiCardVariants({ layout }), className)}>
      <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="text-2xl font-semibold tabular-nums">{value}</span>
        {trendNode}
      </div>
      {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
    </Card>
  )
}
