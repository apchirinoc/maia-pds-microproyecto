import { cva, type VariantProps } from 'class-variance-authority'
import { forwardRef, type HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium w-fit whitespace-nowrap',
  {
    variants: {
      variant: {
        neutral: 'border-transparent bg-secondary text-secondary-foreground',
        info: 'border-transparent bg-brand-100 text-brand-800 dark:bg-brand-900 dark:text-brand-200',
        success:
          'border-transparent bg-success-500/15 text-success-600 dark:text-success-500',
        warning:
          'border-transparent bg-warning-500/15 text-warning-600 dark:text-warning-500',
        danger:
          'border-transparent bg-danger-500/15 text-danger-600 dark:text-danger-500',
        outline: 'text-foreground border-border',
      },
    },
    defaultVariants: {
      variant: 'neutral',
    },
  },
)

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant, ...props }, ref) => (
    <span ref={ref} className={cn(badgeVariants({ variant, className }))} {...props} />
  ),
)
Badge.displayName = 'Badge'
