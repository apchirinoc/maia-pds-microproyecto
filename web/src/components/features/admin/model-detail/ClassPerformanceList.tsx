import { Progress } from '@/components/ui/progress'
import { useI18n } from '@/i18n/I18nProvider'
import { TUMOR_CLASS_COLORS } from '@/lib/tumor-class-colors'
import type { TumorClass } from '@/types/classification'

export interface ClassPerformanceListProps {
  performance: Record<TumorClass, number>
}

export function ClassPerformanceList({ performance }: ClassPerformanceListProps) {
  const { t } = useI18n()

  return (
    <ul className="flex flex-col gap-3">
      {(Object.entries(performance) as [TumorClass, number][]).map(([tumorClass, value]) => (
        <li key={tumorClass}>
          <div className="mb-1 flex items-center justify-between text-sm">
            <span>{t(`classes.${tumorClass}`)}</span>
            <span className="font-medium tabular-nums">{value.toFixed(3)}</span>
          </div>
          <Progress
            value={value * 100}
            className="h-1.5"
            indicatorColor={TUMOR_CLASS_COLORS[tumorClass]}
          />
        </li>
      ))}
    </ul>
  )
}
