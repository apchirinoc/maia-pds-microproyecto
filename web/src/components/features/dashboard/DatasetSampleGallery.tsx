import { ExternalLink } from 'lucide-react'
import { MriThumbnail } from '@/components/shared/MriThumbnail'
import { useI18n } from '@/i18n/I18nProvider'
import { KAGGLE_DATASET_URL, type DatasetSample } from '@/mocks/dashboard.mock'

export interface DatasetSampleGalleryProps {
  samples: DatasetSample[]
}

export function DatasetSampleGallery({ samples }: DatasetSampleGalleryProps) {
  const { t } = useI18n()

  return (
    <div className="grid grid-cols-4 gap-2">
      {samples.map((sample) => (
        <figure key={sample.tumorClass} className="flex min-w-0 flex-col items-center gap-1">
          <div className="aspect-square w-full overflow-hidden rounded-md">
            <MriThumbnail tumorClass={sample.tumorClass} />
          </div>
          <figcaption className="w-full truncate text-center text-[10px] text-muted-foreground">
            {t(`classes.${sample.tumorClass}`)}
          </figcaption>
        </figure>
      ))}
    </div>
  )
}

export function KaggleLink() {
  return (
    <a
      href={KAGGLE_DATASET_URL}
      target="_blank"
      rel="noreferrer"
      className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-primary outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
    >
      Kaggle <ExternalLink className="size-3" />
    </a>
  )
}
