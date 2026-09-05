import { UploadCloud } from 'lucide-react'
import { useRef, useState, type DragEvent } from 'react'
import { useI18n } from '@/i18n/I18nProvider'
import { cn } from '@/lib/utils'

export interface WeightsUploaderProps {
  targetVersion: string
  onFileSelected?: (file: File) => void
}

export function WeightsUploader({ targetVersion, onFileSelected }: WeightsUploaderProps) {
  const { t } = useI18n()
  const inputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [fileName, setFileName] = useState<string | null>(null)

  function handleFiles(files: FileList | null) {
    const file = files?.[0]
    if (!file) return
    setFileName(file.name)
    onFileSelected?.(file)
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragging(false)
    handleFiles(event.dataTransfer.files)
  }

  return (
    <div>
      <p className="mb-1 text-sm font-medium">{t('admin.modelDetail.uploadWeights.title')}</p>
      <p className="mb-3 text-xs text-muted-foreground">{t('admin.modelDetail.uploadWeights.subtitle')}</p>

      <div
        onDragOver={(event) => {
          event.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') inputRef.current?.click()
        }}
        className={cn(
          'flex cursor-pointer flex-col items-center justify-center gap-1.5 rounded-lg border-2 border-dashed border-border p-6 text-center outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring',
          isDragging && 'border-primary bg-accent',
        )}
      >
        <UploadCloud className="size-6 text-muted-foreground" aria-hidden />
        <p className="text-sm font-medium">{fileName ?? t('admin.modelDetail.uploadWeights.dropzoneHint')}</p>
        <p className="text-xs text-muted-foreground">{t('admin.modelDetail.uploadWeights.dropzoneSubHint')}</p>
        <input ref={inputRef} type="file" className="sr-only" onChange={(event) => handleFiles(event.target.files)} />
      </div>

      <dl className="mt-3 flex flex-col gap-1 text-sm">
        <div className="flex items-center justify-between">
          <dt className="text-muted-foreground">{t('admin.modelDetail.uploadWeights.targetVersion')}</dt>
          <dd className="font-medium">
            {targetVersion} {t('admin.modelDetail.uploadWeights.draft')}
          </dd>
        </div>
      </dl>
      <a href="#" className="mt-1 inline-block text-xs text-primary outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring">
        {t('admin.modelDetail.uploadWeights.validationRequired')}
      </a>
    </div>
  )
}
