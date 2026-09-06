import { useState } from 'react'
import { MriThumbnail } from '@/components/shared/MriThumbnail'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useI18n } from '@/i18n/I18nProvider'
import { formatDateTime, formatPercent } from '@/lib/format'
import { TUMOR_CLASS_BADGE_VARIANT, TUMOR_CLASS_COLORS } from '@/lib/tumor-class-colors'
import { cn } from '@/lib/utils'
import type { TumorClass } from '@/types/classification'
import type { UploadRecord } from '@/types/upload'
import { resolveGroundTruthState } from './GroundTruthBadge'
import { GroundTruthCell } from './GroundTruthCell'
import { RecordGroundTruthDialog } from './RecordGroundTruthDialog'
import { UploadStatusBadge } from './UploadStatusBadge'

export interface UploadHistoryTableProps {
  records: UploadRecord[]
  /** Registra la verdad de campo de una carga. La resuelve el service. */
  onRecordGroundTruth: (record: UploadRecord, diagnosis: TumorClass) => Promise<void>
  isRecordingGroundTruth?: boolean
}

export function UploadHistoryTable({
  records,
  onRecordGroundTruth,
  isRecordingGroundTruth = false,
}: UploadHistoryTableProps) {
  const { t, locale } = useI18n()
  const [selectedRecord, setSelectedRecord] = useState<UploadRecord | null>(null)

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t('admin.history.table.mri')}</TableHead>
            <TableHead>{t('admin.history.table.identifier')}</TableHead>
            <TableHead>{t('admin.history.table.date')}</TableHead>
            <TableHead>{t('admin.history.table.origin')}</TableHead>
            <TableHead>{t('admin.history.table.prediction')}</TableHead>
            <TableHead>{t('admin.history.table.confidence')}</TableHead>
            <TableHead>{t('admin.history.table.groundTruth')}</TableHead>
            <TableHead>{t('admin.history.table.status')}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {records.map((record) => {
            const groundTruthState = resolveGroundTruthState(record.prediction, record.groundTruth)

            return (
              <TableRow
                key={record.id}
                data-ground-truth={groundTruthState}
                // La fila entera se tiñe cuando el diagnóstico confirmado
                // contradice al modelo: es el caso que hay que ver de un vistazo.
                className={cn(
                  'data-[ground-truth=mismatch]:bg-danger-500/5',
                  'data-[ground-truth=mismatch]:hover:bg-danger-500/10',
                )}
              >
                <TableCell>
                  <div className="size-10 overflow-hidden rounded-md">
                    <MriThumbnail tumorClass={record.prediction} />
                  </div>
                </TableCell>
                <TableCell>
                  <div className="font-medium">{record.id}</div>
                  <div className="text-xs text-muted-foreground">{record.fileName}</div>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {formatDateTime(record.capturedAt, locale)}
                </TableCell>
                <TableCell className="text-muted-foreground">{record.countryName}</TableCell>
                <TableCell>
                  <Badge variant={TUMOR_CLASS_BADGE_VARIANT[record.prediction]}>
                    {t(`classes.${record.prediction}`)}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <span className="w-10 tabular-nums">
                      {formatPercent(record.confidence, locale)}
                    </span>
                    <Progress
                      value={record.confidence}
                      className="h-1.5 w-20"
                      indicatorColor={TUMOR_CLASS_COLORS[record.prediction]}
                    />
                  </div>
                </TableCell>
                <TableCell>
                  <GroundTruthCell
                    record={record}
                    disabled={isRecordingGroundTruth}
                    onRecordClick={setSelectedRecord}
                  />
                </TableCell>
                <TableCell>
                  <UploadStatusBadge status={record.status} />
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>

      <RecordGroundTruthDialog
        record={selectedRecord}
        isSubmitting={isRecordingGroundTruth}
        onClose={() => setSelectedRecord(null)}
        onConfirm={onRecordGroundTruth}
      />
    </>
  )
}
