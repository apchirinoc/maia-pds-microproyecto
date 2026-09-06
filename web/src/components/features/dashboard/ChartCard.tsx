import type { ReactNode } from 'react'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

export interface ChartCardProps {
  title: string
  subtitle?: string
  action?: ReactNode
  footer?: ReactNode
  isLoading?: boolean
  className?: string
  contentClassName?: string
  children: ReactNode
}

export function ChartCard({
  title,
  subtitle,
  action,
  footer,
  isLoading,
  className,
  contentClassName,
  children,
}: ChartCardProps) {
  return (
    <Card className={cn('flex min-h-0 flex-col overflow-hidden', className)}>
      <div className="flex shrink-0 items-start justify-between gap-2 px-4 pb-2 pt-3">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold leading-tight">{title}</h3>
          {subtitle && <p className="truncate text-xs text-muted-foreground">{subtitle}</p>}
        </div>
        {action}
      </div>

      <div className={cn('min-h-0 flex-1 px-4 pb-3', contentClassName)}>
        {isLoading ? <Skeleton className="size-full min-h-24" /> : children}
      </div>

      {footer && <div className="shrink-0 px-4 pb-3">{footer}</div>}
    </Card>
  )
}
