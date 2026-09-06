import { cva } from 'class-variance-authority'
import type { CSSProperties } from 'react'
import { MriThumbnail } from '@/components/shared/MriThumbnail'
import { useI18n } from '@/i18n/I18nProvider'
import { formatPercent } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { PredictionExplanation, TumorClass } from '@/types/classification'
import type { SelectedImage } from './ImageDropzone'

/** Color cálido del mapa: sobre una MRI en grises no compite con la anatomía. */
const HEAT_COLOR = '#f97316'

const influenceLayerVariants = cva(
  'pointer-events-none absolute inset-0 transition-opacity duration-300 motion-reduce:transition-none',
  {
    variants: {
      state: {
        visible: 'opacity-100',
        hidden: 'opacity-0',
      },
    },
    defaultVariants: { state: 'visible' },
  },
)

export interface InfluenceMapOverlayProps {
  /** Mapa y método, tal y como los declara el artefacto del modelo. */
  explanation: PredictionExplanation
  predictedClass: TumorClass
  selectedImage: SelectedImage | null
  visible: boolean
  className?: string
}

/**
 * Superpone el mapa de influencia sobre la imagen MRI analizada.
 *
 * El mapa llega como imagen cuya intensidad vive en el canal alfa, así que se
 * usa tal cual como máscara CSS de una capa de color: el cliente no decodifica
 * ni recolorea nada. El método de explicabilidad se calcula dentro del
 * artefacto (patrón «Explainable Predictions»), aquí solo se pinta.
 */
export function InfluenceMapOverlay({
  explanation,
  predictedClass,
  selectedImage,
  visible,
  className,
}: InfluenceMapOverlayProps) {
  const { t, locale } = useI18n()

  const maskStyle: CSSProperties = {
    backgroundColor: HEAT_COLOR,
    maskImage: `url("${explanation.influenceMapDataUri}")`,
    WebkitMaskImage: `url("${explanation.influenceMapDataUri}")`,
    maskSize: '100% 100%',
    WebkitMaskSize: '100% 100%',
    maskRepeat: 'no-repeat',
    WebkitMaskRepeat: 'no-repeat',
    mixBlendMode: 'screen',
  }

  return (
    <figure className={cn('flex flex-col gap-2', className)}>
      {/* `isolate` confina el `mix-blend-mode` de la capa de calor a esta caja. */}
      <div className="relative isolate aspect-square w-full overflow-hidden rounded-lg border border-border bg-black">
        {selectedImage?.kind === 'upload' ? (
          <img
            src={selectedImage.previewUrl}
            alt={t('analyze.step3.explanationHint')}
            className="size-full object-cover"
          />
        ) : (
          <MriThumbnail
            tumorClass={selectedImage?.kind === 'sample' ? selectedImage.tumorClass : predictedClass}
          />
        )}
        <div
          aria-hidden
          style={maskStyle}
          className={influenceLayerVariants({ state: visible ? 'visible' : 'hidden' })}
        />
      </div>

      <div
        className={cn(
          'flex items-center gap-2 text-[11px] text-muted-foreground transition-opacity duration-300 motion-reduce:transition-none',
          visible ? 'opacity-100' : 'opacity-0',
        )}
      >
        <span className="tabular-nums">{formatPercent(0, locale, 0)}</span>
        <span
          aria-hidden
          className="h-1.5 flex-1 rounded-full ring-1 ring-inset ring-border"
          style={{ backgroundImage: `linear-gradient(to right, transparent, ${HEAT_COLOR})` }}
        />
        <span className="tabular-nums">{formatPercent(100, locale, 0)}</span>
      </div>

      <figcaption className="sr-only">
        {t('analyze.step3.explanation')} · {t('analyze.step3.explanationHint')} ·{' '}
        {explanation.methodLabel}
      </figcaption>
    </figure>
  )
}
