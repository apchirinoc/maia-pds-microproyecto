import { Progress } from '@/components/ui/progress'
import { useI18n } from '@/i18n/I18nProvider'
import { formatPercent } from '@/lib/format'
import { TUMOR_CLASS_COLORS } from '@/lib/tumor-class-colors'
import type { TumorClass } from '@/types/classification'

export interface ConfidenceBarListProps {
  confidenceByClass: Record<TumorClass, number>
}

export function ConfidenceBarList({ confidenceByClass }: ConfidenceBarListProps) {
  const { t, locale } = useI18n()

  const sorted = (Object.entries(confidenceByClass) as [TumorClass, number][]).sort(
    (a, b) => b[1] - a[1],
  )

  return (
    <ul className="flex flex-col gap-3">
      {sorted.map(([tumorClass, value]) => (
        <li key={tumorClass}>
          <div className="mb-1 flex items-center justify-between text-sm">
            <span>{t(`classes.${tumorClass}`)}</span>
            <span className="font-medium tabular-nums">{formatPercent(value, locale)}</span>
          </div>
          <Progress value={value} className="h-1.5" indicatorColor={TUMOR_CLASS_COLORS[tumorClass]} />
        </li>
      ))}
    </ul>
  )
}
