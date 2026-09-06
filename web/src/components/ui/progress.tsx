import * as ProgressPrimitive from '@radix-ui/react-progress'
import { cva, type VariantProps } from 'class-variance-authority'
import { forwardRef } from 'react'
import { cn } from '@/lib/utils'

const progressIndicatorVariants = cva('h-full w-full flex-1 transition-transform', {
  variants: {
    tone: {
      default: 'bg-primary',
      success: 'bg-success-500',
      warning: 'bg-warning-500',
      danger: 'bg-danger-500',
    },
  },
  defaultVariants: { tone: 'default' },
})

export interface ProgressProps
  extends React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root>,
    VariantProps<typeof progressIndicatorVariants> {
  value: number
  indicatorColor?: string
}

export const Progress = forwardRef<React.ElementRef<typeof ProgressPrimitive.Root>, ProgressProps>(
  ({ className, value, tone, indicatorColor, ...props }, ref) => (
    <ProgressPrimitive.Root
      ref={ref}
      className={cn('relative h-2 w-full overflow-hidden rounded-full bg-muted', className)}
      {...props}
    >
      <ProgressPrimitive.Indicator
        className={cn(progressIndicatorVariants({ tone: indicatorColor ? null : tone }))}
        style={{
          transform: `translateX(-${100 - Math.min(100, Math.max(0, value))}%)`,
          backgroundColor: indicatorColor,
        }}
      />
    </ProgressPrimitive.Root>
  ),
)
Progress.displayName = ProgressPrimitive.Root.displayName
