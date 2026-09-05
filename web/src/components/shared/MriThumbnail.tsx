import { useState } from 'react'
import { SAMPLE_IMAGES_BY_CLASS } from '@/lib/mri-samples'
import { cn } from '@/lib/utils'
import type { TumorClass } from '@/types/classification'

export interface MriThumbnailProps {
  tumorClass: TumorClass
  className?: string
  alt?: string
}

export function MriThumbnail({ tumorClass, className, alt }: MriThumbnailProps) {
  const [hasError, setHasError] = useState(false)
  const sample = SAMPLE_IMAGES_BY_CLASS[tumorClass]

  if (hasError) {
    return (
      <div
        role="img"
        aria-label={alt ?? `MRI sample · ${tumorClass}`}
        className={cn(
          'flex h-full w-full items-center justify-center rounded-md bg-zinc-900 text-[10px] text-zinc-500 font-mono',
          className,
        )}
      >
        MRI · {tumorClass}
      </div>
    )
  }

  return (
    <img
      src={sample.url}
      alt={alt ?? `MRI sample · ${tumorClass} (${sample.fileName})`}
      loading="lazy"
      onError={() => setHasError(true)}
      className={cn(
        'block h-full w-full select-none rounded-md bg-black object-cover transition-transform duration-200',
        className,
      )}
    />
  )
}

