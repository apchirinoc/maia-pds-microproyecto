import { UploadCloud, X } from 'lucide-react'
import { useRef, useState, type DragEvent } from 'react'
import { Button } from '@/components/ui/button'
import { MriThumbnail } from '@/components/shared/MriThumbnail'
import { useI18n } from '@/i18n/I18nProvider'
import { cn } from '@/lib/utils'
import type { TumorClass } from '@/types/classification'

export type SelectedImage =
  | { kind: 'upload'; file: File; previewUrl: string }
  | { kind: 'sample'; tumorClass: TumorClass; fileName: string }

export interface ImageDropzoneProps {
  selectedImage: SelectedImage | null
  onFileSelected: (file: File) => void
  onClear: () => void
}

const ACCEPTED_TYPES = ['image/jpeg', 'image/png']
const MAX_SIZE_BYTES = 8 * 1024 * 1024

export function ImageDropzone({ selectedImage, onFileSelected, onClear }: ImageDropzoneProps) {
  const { t } = useI18n()
  const inputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)

  function handleFiles(files: FileList | null) {
    const file = files?.[0]
    if (!file) return
    if (!ACCEPTED_TYPES.includes(file.type) || file.size > MAX_SIZE_BYTES) return
    onFileSelected(file)
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragging(false)
    handleFiles(event.dataTransfer.files)
  }

  if (selectedImage) {
    return (
      <div className="relative aspect-square w-full overflow-hidden rounded-lg border border-border">
        {selectedImage.kind === 'upload' ? (
          <img
            src={selectedImage.previewUrl}
            alt="MRI preview"
            className="size-full object-cover"
          />
        ) : (
          <MriThumbnail tumorClass={selectedImage.tumorClass} />
        )}
        <div className="absolute bottom-2 left-2 rounded bg-black/70 px-2 py-0.5 text-[11px] text-white">
          {selectedImage.kind === 'upload' ? selectedImage.file.name : selectedImage.fileName}
        </div>
        <button
          type="button"
          onClick={onClear}
          aria-label={t('common.cancel')}
          className="absolute right-2 top-2 flex size-7 items-center justify-center rounded-full bg-black/70 text-white outline-none transition-colors hover:bg-black/90 focus-visible:ring-2 focus-visible:ring-ring"
        >
          <X className="size-4" />
        </button>
      </div>
    )
  }

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault()
        setIsDragging(true)
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      className={cn(
        'flex aspect-square w-full flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-border p-6 text-center transition-colors',
        isDragging && 'border-primary bg-accent',
      )}
    >
      <UploadCloud className="size-8 text-muted-foreground" aria-hidden />
      <div>
        <p className="text-sm font-medium">{t('analyze.step1.dropzoneTitle')}</p>
        <p className="mt-1 text-xs text-muted-foreground">{t('analyze.step1.dropzoneHint')}</p>
      </div>
      <Button type="button" variant="outline" size="sm" onClick={() => inputRef.current?.click()}>
        {t('analyze.step1.selectFile')}
      </Button>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES.join(',')}
        className="sr-only"
        onChange={(event) => handleFiles(event.target.files)}
      />
    </div>
  )
}
