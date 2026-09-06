import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useI18n } from '@/i18n/I18nProvider'
import { TUMOR_CLASS_BADGE_VARIANT } from '@/lib/tumor-class-colors'
import { TUMOR_CLASSES, type TumorClass } from '@/types/classification'
import type { UploadRecord } from '@/types/upload'

export interface RecordGroundTruthDialogProps {
  /** Carga cuyo diagnóstico se registra; `null` mantiene cerrado el diálogo. */
  record: UploadRecord | null
  isSubmitting?: boolean
  onClose: () => void
  onConfirm: (record: UploadRecord, diagnosis: TumorClass) => Promise<void>
}

export function RecordGroundTruthDialog({
  record,
  isSubmitting = false,
  onClose,
  onConfirm,
}: RecordGroundTruthDialogProps) {
  const { t } = useI18n()
  // Cadena vacía = todavía sin elegir; Radix muestra entonces el placeholder.
  const [diagnosis, setDiagnosis] = useState<TumorClass | ''>('')
  const [recordId, setRecordId] = useState<string | null>(null)

  // Al abrir se parte del diagnóstico ya confirmado si lo hubiera, para que
  // corregir una confirmación no obligue a recordarla de memoria. El ajuste se
  // hace durante el render y no en un efecto: React lo reintenta de inmediato
  // sin pintar el valor obsoleto ni encadenar un segundo render.
  const currentRecordId = record?.id ?? null
  if (currentRecordId !== recordId) {
    setRecordId(currentRecordId)
    setDiagnosis(record?.groundTruth?.diagnosis ?? '')
  }

  async function handleConfirm() {
    if (record === null || diagnosis === '') return
    try {
      await onConfirm(record, diagnosis)
      onClose()
    } catch {
      // El registro no se ha guardado: se deja el diálogo abierto con lo que el
      // especialista había seleccionado para que pueda reintentar.
    }
  }

  return (
    <Dialog
      open={record !== null}
      onOpenChange={(open) => {
        if (!open && !isSubmitting) onClose()
      }}
    >
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{t('admin.history.groundTruth.dialogTitle')}</DialogTitle>
          <DialogDescription>{t('admin.history.groundTruth.dialogBody')}</DialogDescription>
        </DialogHeader>

        {record && (
          <div className="mb-4 flex items-center justify-between gap-3 rounded-lg border border-border bg-muted/40 px-3 py-2">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{record.id}</p>
              <p className="truncate text-xs text-muted-foreground">{record.fileName}</p>
            </div>
            <div className="flex flex-col items-end gap-1">
              <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
                {t('admin.history.table.prediction')}
              </span>
              <Badge variant={TUMOR_CLASS_BADGE_VARIANT[record.prediction]}>
                {t(`classes.${record.prediction}`)}
              </Badge>
            </div>
          </div>
        )}

        <div className="flex flex-col gap-1.5">
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {t('admin.history.table.groundTruth')}
          </span>
          <Select
            value={diagnosis}
            disabled={isSubmitting}
            onValueChange={(value) => setDiagnosis(value as TumorClass)}
          >
            <SelectTrigger aria-label={t('admin.history.table.groundTruth')}>
              <SelectValue placeholder={t('admin.history.groundTruth.unconfirmed')} />
            </SelectTrigger>
            <SelectContent>
              {TUMOR_CLASSES.map((tumorClass) => (
                <SelectItem key={tumorClass} value={tumorClass}>
                  {t(`classes.${tumorClass}`)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" disabled={isSubmitting} onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button
            type="button"
            disabled={diagnosis === '' || isSubmitting}
            onClick={() => {
              void handleConfirm()
            }}
          >
            {t('common.save')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
