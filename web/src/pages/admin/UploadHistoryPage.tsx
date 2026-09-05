import { useCallback, useMemo, useState } from 'react'
import { Database, Download } from 'lucide-react'
import { AdminShell } from '@/components/layout/AdminShell'
import { KpiCard } from '@/components/features/dashboard/KpiCard'
import { ClassFilterTabs } from '@/components/features/admin/history/ClassFilterTabs'
import { UploadHistoryTable } from '@/components/features/admin/history/UploadHistoryTable'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Pagination } from '@/components/ui/pagination'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useI18n } from '@/i18n/I18nProvider'
import { formatNumber, formatPercent } from '@/lib/format'
import { useAuth } from '@/hooks/useAuth'
import {
  useAddUploadsToDataset,
  useExportUploadHistoryCsv,
  useRecordGroundTruth,
  useUploadHistory,
  useUploadHistorySummary,
} from '@/hooks/useUploadHistory'
import type { TumorClass } from '@/types/classification'
import type { UploadRecord } from '@/types/upload'

const PAGE_SIZE_OPTIONS = [5, 10, 25, 50]

/** Sin dato: la precisión medida no existe mientras no haya ninguna confirmada. */
const EMPTY_METRIC = '—'

export function UploadHistoryPage() {
  const { t, locale } = useI18n()
  const { session } = useAuth()
  const summaryQuery = useUploadHistorySummary()
  const exportMutation = useExportUploadHistoryCsv()
  const addToDatasetMutation = useAddUploadsToDataset()
  const recordGroundTruthMutation = useRecordGroundTruth()

  const [tumorClass, setTumorClass] = useState<TumorClass | 'all'>('all')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(5)

  const filters = useMemo(() => ({ tumorClass, page, pageSize }), [tumorClass, page, pageSize])
  const historyQuery = useUploadHistory(filters)

  const summary = summaryQuery.data
  const groundTruth = summary?.groundTruth
  const result = historyQuery.data
  const totalPages = result ? Math.max(1, Math.ceil(result.total / pageSize)) : 1

  function handleFilterChange(next: TumorClass | 'all') {
    setTumorClass(next)
    setPage(1)
  }

  async function handleExportCsv() {
    const blob = await exportMutation.mutateAsync()
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'brainneuroscan-upload-history.csv'
    anchor.click()
    URL.revokeObjectURL(url)
  }

  function handleAddPendingToDataset() {
    const pendingIds = (result?.items ?? [])
      .filter((record) => record.status === 'pending')
      .map((record) => record.id)
    if (pendingIds.length === 0) return
    addToDatasetMutation.mutate(pendingIds)
  }

  /**
   * Registra la verdad de campo de una carga.
   *
   * La fuente es `specialist_review` porque es lo que describe honestamente una
   * confirmación hecha desde esta pantalla: la lectura de un especialista. Un
   * informe de anatomía patológica entra por la vía documental, no por aquí.
   */
  const handleRecordGroundTruth = useCallback(
    async (record: UploadRecord, diagnosis: TumorClass) => {
      await recordGroundTruthMutation.mutateAsync({
        uploadId: record.id,
        diagnosis,
        confirmedBy: session?.username ?? 'unknown',
        source: 'specialist_review',
      })
    },
    [recordGroundTruthMutation, session],
  )

  return (
    <AdminShell>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{t('admin.history.title')}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t('admin.history.subtitle')}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleExportCsv} disabled={exportMutation.isPending}>
            <Download /> {t('admin.history.exportCsv')}
          </Button>
          <Button onClick={handleAddPendingToDataset} disabled={addToDatasetMutation.isPending}>
            <Database /> {t('admin.history.addToDataset')}
          </Button>
        </div>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <KpiCard
          isLoading={summaryQuery.isLoading}
          label={t('admin.history.kpi.totalUploads')}
          value={summary ? formatNumber(summary.totalUploads, locale) : ''}
        />
        <KpiCard
          isLoading={summaryQuery.isLoading}
          label={t('admin.history.kpi.pendingReview')}
          value={summary ? formatNumber(summary.pendingReview, locale) : ''}
        />
        <KpiCard
          isLoading={summaryQuery.isLoading}
          label={t('admin.history.kpi.avgConfidence')}
          value={summary ? formatPercent(summary.averageConfidence, locale) : ''}
        />
        <KpiCard
          isLoading={summaryQuery.isLoading}
          label={t('admin.history.kpi.discarded')}
          value={summary ? formatNumber(summary.discarded, locale) : ''}
        />
        {/*
          Los dos KPI del circuito de verdad de campo. Se calculan en el service
          a partir de los registros, nunca como constantes. Sin cobertura la
          precisión medida no es representativa: por eso van juntos y ambos
          muestran su fracción exacta.
        */}
        <KpiCard
          isLoading={summaryQuery.isLoading}
          label={t('admin.history.kpi.groundTruthCoverage')}
          value={groundTruth ? formatPercent(groundTruth.coverage, locale) : ''}
          hint={
            groundTruth
              ? `${formatNumber(groundTruth.confirmedUploads, locale)} / ${formatNumber(groundTruth.totalUploads, locale)}`
              : undefined
          }
        />
        <KpiCard
          isLoading={summaryQuery.isLoading}
          label={t('admin.history.kpi.measuredAccuracy')}
          value={
            groundTruth
              ? groundTruth.measuredAccuracy === null
                ? EMPTY_METRIC
                : formatPercent(groundTruth.measuredAccuracy, locale)
              : ''
          }
          hint={
            groundTruth
              ? `${formatNumber(groundTruth.correctPredictions, locale)} / ${formatNumber(groundTruth.confirmedUploads, locale)}`
              : undefined
          }
        />
      </div>

      <Card>
        <CardContent className="pt-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <ClassFilterTabs value={tumorClass} onValueChange={handleFilterChange} />

            <div className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground">{t('admin.history.lastDays')}</span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">{t('admin.history.pageSize')}</span>
                <Select
                  value={String(pageSize)}
                  onValueChange={(value) => {
                    setPageSize(Number(value))
                    setPage(1)
                  }}
                >
                  <SelectTrigger className="w-16">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PAGE_SIZE_OPTIONS.map((size) => (
                      <SelectItem key={size} value={String(size)}>
                        {size}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {result && (
            <UploadHistoryTable
              records={result.items}
              onRecordGroundTruth={handleRecordGroundTruth}
              isRecordingGroundTruth={recordGroundTruthMutation.isPending}
            />
          )}

          {result && (
            <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <span className="text-xs text-muted-foreground">
                {t('admin.history.showing', {
                  from: (page - 1) * pageSize + 1,
                  to: Math.min(page * pageSize, result.total),
                  total: formatNumber(result.total, locale),
                  pending: summary ? formatNumber(summary.pendingReview, locale) : '',
                })}
              </span>
              <Pagination
                page={page}
                totalPages={totalPages}
                onPageChange={setPage}
                previousLabel={t('admin.history.previous')}
                nextLabel={t('admin.history.next')}
              />
            </div>
          )}
        </CardContent>
      </Card>
    </AdminShell>
  )
}
