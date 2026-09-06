import { Download, Eye, EyeOff, RotateCcw, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { Toggle } from '@/components/ui/toggle'
import { useI18n } from '@/i18n/I18nProvider'
import { formatPercent } from '@/lib/format'
import { TUMOR_CLASS_BADGE_VARIANT } from '@/lib/tumor-class-colors'
import type { ActiveModelInfo, ClassificationResult } from '@/types/classification'
import { ConfidenceBarList } from './ConfidenceBarList'
import type { SelectedImage } from './ImageDropzone'
import { InfluenceMapOverlay } from './InfluenceMapOverlay'

export type ClassificationStatus = 'empty' | 'ready' | 'loading' | 'result'

export interface ClassificationResultPanelProps {
  status: ClassificationStatus
  countryName: string | null
  /** Declarado por el artefacto del modelo, nunca escrito a mano en la UI. */
  modelInfo: ActiveModelInfo | null
  result: ClassificationResult | null
  /** Imagen analizada, sobre la que se dibuja el mapa de influencia. */
  selectedImage: SelectedImage | null
  onClassify: () => void
  onNewImage: () => void
  onDownloadReport: () => void
}

export function ClassificationResultPanel({
  status,
  countryName,
  modelInfo,
  result,
  selectedImage,
  onClassify,
  onNewImage,
  onDownloadReport,
}: ClassificationResultPanelProps) {
  const { t, locale } = useI18n()
  const [isOverlayVisible, setIsOverlayVisible] = useState(true)

  if (status === 'empty') {
    return (
      <div className="flex h-full min-h-64 flex-col items-center justify-center gap-2 text-center text-sm text-muted-foreground">
        <Sparkles className="size-6" aria-hidden />
        <p>{t('analyze.step3.emptyState')}</p>
      </div>
    )
  }

  if (status === 'loading') {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-16 w-full rounded-lg" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>
    )
  }

  if (status === 'ready') {
    return (
      <div className="flex h-full flex-col justify-between gap-6">
        <dl className="grid grid-cols-1 gap-3 text-sm">
          <div className="flex items-center justify-between">
            <dt className="text-muted-foreground">{t('analyze.step3.model')}</dt>
            <dd className="font-medium">{modelInfo?.modelVersion ?? '—'}</dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-muted-foreground">{t('analyze.step3.preprocess')}</dt>
            <dd className="font-medium">{modelInfo?.preprocessLabel ?? '—'}</dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-muted-foreground">{t('analyze.step3.origin')}</dt>
            <dd className="font-medium">{countryName}</dd>
          </div>
        </dl>
        <Button onClick={onClassify} className="w-full">
          {t('analyze.step3.classify')}
        </Button>
      </div>
    )
  }

  if (!result) return null

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="rounded-lg bg-primary p-4 text-primary-foreground">
        <Badge variant={TUMOR_CLASS_BADGE_VARIANT[result.predictedClass]} className="mb-2 bg-white/15 text-inherit">
          {t('analyze.step3.resultBadge')}
        </Badge>
        <p className="text-lg font-semibold">
          {t(`classes.${result.predictedClass}`)}{' '}
          <span className="font-normal opacity-90">
            {formatPercent(result.confidenceByClass[result.predictedClass], locale)}
          </span>
        </p>
        <p className="mt-1 text-xs opacity-90">{result.description}</p>
      </div>

      <ConfidenceBarList confidenceByClass={result.confidenceByClass} />

      {result.explanation && (
        <section className="flex flex-col gap-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="text-sm font-medium">{t('analyze.step3.explanation')}</h3>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {t('analyze.step3.explanationHint')}
              </p>
            </div>
            <Toggle
              size="sm"
              pressed={isOverlayVisible}
              onPressedChange={setIsOverlayVisible}
              aria-label={
                isOverlayVisible ? t('analyze.step3.hideOverlay') : t('analyze.step3.showOverlay')
              }
              className="shrink-0 border border-border"
            >
              {isOverlayVisible ? (
                <EyeOff className="size-3.5" aria-hidden />
              ) : (
                <Eye className="size-3.5" aria-hidden />
              )}
              {isOverlayVisible ? t('analyze.step3.hideOverlay') : t('analyze.step3.showOverlay')}
            </Toggle>
          </div>

          <InfluenceMapOverlay
            explanation={result.explanation}
            predictedClass={result.predictedClass}
            selectedImage={selectedImage}
            visible={isOverlayVisible}
          />

          <p className="text-xs text-muted-foreground">
            <span className="font-medium text-foreground">
              {t('analyze.step3.explanationMethod')}
            </span>{' '}
            · {result.explanation.methodLabel}
          </p>
        </section>
      )}

      <Separator className="mt-auto" />

      <div className="flex gap-2">
        <Button variant="outline" className="flex-1" onClick={onNewImage}>
          <RotateCcw /> {t('analyze.step3.newImage')}
        </Button>
        <Button className="flex-1" onClick={onDownloadReport}>
          <Download /> {t('analyze.step3.downloadReport')}
        </Button>
      </div>
    </div>
  )
}
