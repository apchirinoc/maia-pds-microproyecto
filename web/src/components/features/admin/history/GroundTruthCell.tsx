import { Stethoscope } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { useI18n } from '@/i18n/I18nProvider'
import { formatDateTime } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { UploadRecord } from '@/types/upload'
import { GroundTruthBadge, resolveGroundTruthState } from './GroundTruthBadge'

export interface GroundTruthCellProps {
  record: UploadRecord
  /** Abre el diálogo de registro para esta carga. */
  onRecordClick: (record: UploadRecord) => void
  disabled?: boolean
}

/**
 * Celda «Diagnóstico confirmado»: muestra la verdad de campo de la carga —o su
 * ausencia—, marca la discrepancia con la predicción y ofrece la acción de
 * registrarla o corregirla.
 */
export function GroundTruthCell({ record, onRecordClick, disabled = false }: GroundTruthCellProps) {
  const { t, locale } = useI18n()
  const state = resolveGroundTruthState(record.prediction, record.groundTruth)
  const groundTruth = record.groundTruth

  return (
    <div className="flex items-center gap-2">
      <div className="flex min-w-28 flex-col items-start gap-0.5">
        {groundTruth === null ? (
          <GroundTruthBadge prediction={record.prediction} groundTruth={null} />
        ) : (
          <Tooltip>
            <TooltipTrigger asChild>
              <GroundTruthBadge prediction={record.prediction} groundTruth={groundTruth} />
            </TooltipTrigger>
            <TooltipContent>
              {groundTruth.confirmedBy} · {formatDateTime(groundTruth.confirmedAt, locale)}
            </TooltipContent>
          </Tooltip>
        )}

        {state !== 'unconfirmed' && (
          <span
            className={cn(
              'text-[11px] font-medium',
              state === 'mismatch'
                ? 'text-danger-600 dark:text-danger-500'
                : 'text-muted-foreground',
            )}
          >
            {state === 'mismatch'
              ? t('admin.history.groundTruth.mismatch')
              : t('admin.history.groundTruth.match')}
          </span>
        )}
      </div>

      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-8 shrink-0"
            disabled={disabled}
            aria-label={t('admin.history.groundTruth.record')}
            onClick={() => onRecordClick(record)}
          >
            <Stethoscope />
          </Button>
        </TooltipTrigger>
        <TooltipContent>{t('admin.history.groundTruth.record')}</TooltipContent>
      </Tooltip>
    </div>
  )
}
