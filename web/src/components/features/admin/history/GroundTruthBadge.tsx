import { cva, type VariantProps } from 'class-variance-authority'
import { CircleDashed, ShieldCheck, TriangleAlert } from 'lucide-react'
import { forwardRef, type HTMLAttributes } from 'react'
import { useI18n } from '@/i18n/I18nProvider'
import { cn } from '@/lib/utils'
import type { TumorClass } from '@/types/classification'
import type { GroundTruthDiagnosis } from '@/types/upload'

const groundTruthBadgeVariants = cva(
  'inline-flex w-fit items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors',
  {
    variants: {
      state: {
        // Sin confirmar: borde discontinuo, sin color. No es un error, es una
        // ausencia de dato, y no debe competir visualmente con la discrepancia.
        unconfirmed: 'border-dashed border-border text-muted-foreground',
        match: 'border-transparent bg-success-500/15 text-success-600 dark:text-success-500',
        // Discrepancia: el caso que importa. Lleva borde propio además del
        // fondo para que se distinga aunque no se perciba bien el color.
        mismatch: 'border-danger-500/50 bg-danger-500/15 text-danger-600 dark:text-danger-500',
      },
    },
    defaultVariants: { state: 'unconfirmed' },
  },
)

export type GroundTruthState = NonNullable<VariantProps<typeof groundTruthBadgeVariants>['state']>

/**
 * Compara la predicción del modelo con el diagnóstico confirmado.
 * `unconfirmed` cuando todavía no hay verdad de campo.
 */
export function resolveGroundTruthState(
  prediction: TumorClass,
  groundTruth: GroundTruthDiagnosis | null,
): GroundTruthState {
  if (groundTruth === null) return 'unconfirmed'
  return groundTruth.diagnosis === prediction ? 'match' : 'mismatch'
}

const ICON_BY_STATE = {
  unconfirmed: CircleDashed,
  match: ShieldCheck,
  mismatch: TriangleAlert,
} as const

export interface GroundTruthBadgeProps extends Omit<HTMLAttributes<HTMLSpanElement>, 'children'> {
  prediction: TumorClass
  groundTruth: GroundTruthDiagnosis | null
}

export const GroundTruthBadge = forwardRef<HTMLSpanElement, GroundTruthBadgeProps>(
  ({ prediction, groundTruth, className, ...props }, ref) => {
    const { t } = useI18n()
    const state = resolveGroundTruthState(prediction, groundTruth)
    const Icon = ICON_BY_STATE[state]

    return (
      <span ref={ref} className={cn(groundTruthBadgeVariants({ state }), className)} {...props}>
        <Icon className="size-3.5 shrink-0" aria-hidden />
        {groundTruth === null
          ? t('admin.history.groundTruth.unconfirmed')
          : t(`classes.${groundTruth.diagnosis}`)}
      </span>
    )
  },
)
GroundTruthBadge.displayName = 'GroundTruthBadge'
