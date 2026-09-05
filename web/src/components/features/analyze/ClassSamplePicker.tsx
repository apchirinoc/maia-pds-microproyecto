import { MriThumbnail } from '@/components/shared/MriThumbnail'
import { useI18n } from '@/i18n/I18nProvider'
import { cn } from '@/lib/utils'
import type { DatasetSample } from '@/mocks/dashboard.mock'
import type { TumorClass } from '@/types/classification'

export interface ClassSamplePickerProps {
  samples: DatasetSample[]
  selectedTumorClass: TumorClass | null
  onSelectSample: (sample: DatasetSample) => void
}

export function ClassSamplePicker({ samples, selectedTumorClass, onSelectSample }: ClassSamplePickerProps) {
  const { t } = useI18n()

  return (
    <div>
      <p className="mb-2 text-xs text-muted-foreground">{t('analyze.step1.orSample')}</p>
      <div className="grid grid-cols-4 gap-2">
        {samples.map((sample) => (
          <button
            key={sample.tumorClass}
            type="button"
            onClick={() => onSelectSample(sample)}
            className={cn(
              'aspect-square overflow-hidden rounded-md outline-none ring-primary transition-shadow focus-visible:ring-2',
              selectedTumorClass === sample.tumorClass && 'ring-2',
            )}
            aria-pressed={selectedTumorClass === sample.tumorClass}
            aria-label={t(`classes.${sample.tumorClass}`)}
          >
            <MriThumbnail tumorClass={sample.tumorClass} />
          </button>
        ))}
      </div>
    </div>
  )
}
