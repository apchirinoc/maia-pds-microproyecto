import { useMemo, useState } from 'react'
import { Boxes } from 'lucide-react'
import { AdminShell } from '@/components/layout/AdminShell'
import { KpiCard } from '@/components/features/dashboard/KpiCard'
import { ModelsTable } from '@/components/features/admin/models/ModelsTable'
import { RegistryModelPicker } from '@/components/features/admin/model-detail/RegistryModelPicker'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { useI18n } from '@/i18n/I18nProvider'
import { formatDate, formatNumber, formatPercent } from '@/lib/format'
import {
  useDeployModel,
  useModelRegistrySummary,
  useModels,
  useRevertModel,
} from '@/hooks/useModels'
import type { ModelStatus } from '@/types/model'

export function ModelManagementPage() {
  const { t, locale } = useI18n()
  const summaryQuery = useModelRegistrySummary()
  const modelsQuery = useModels()
  const deployMutation = useDeployModel()
  const revertMutation = useRevertModel()

  const [statusFilter, setStatusFilter] = useState<ModelStatus | 'all'>('all')
  const [pickerOpen, setPickerOpen] = useState(false)

  const filteredModels = useMemo(() => {
    if (!modelsQuery.data) return []
    if (statusFilter === 'all') return modelsQuery.data
    return modelsQuery.data.filter((model) => model.status === statusFilter)
  }, [modelsQuery.data, statusFilter])

  const summary = summaryQuery.data

  return (
    <AdminShell>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{t('admin.models.title')}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t('admin.models.subtitle')}</p>
        </div>

        <Dialog open={pickerOpen} onOpenChange={setPickerOpen}>
          <DialogTrigger asChild>
            <Button>
              <Boxes /> {t('admin.models.uploadNew')}
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t('admin.models.uploadNew')}</DialogTitle>
              <DialogDescription>
                {t('admin.modelDetail.registryPicker.subtitle')}
              </DialogDescription>
            </DialogHeader>
            <RegistryModelPicker onActivated={() => setPickerOpen(false)} />
          </DialogContent>
        </Dialog>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          isLoading={summaryQuery.isLoading}
          label={t('admin.models.kpi.production')}
          value={summary ? `${summary.productionModel.name} ${summary.productionModel.version}` : ''}
          hint={summary ? t('admin.models.kpi.activeSince', { date: formatDate(summary.activeSince, locale) }) : undefined}
        />
        <KpiCard
          isLoading={summaryQuery.isLoading}
          label={t('admin.models.kpi.accuracyTest')}
          value={summary ? formatPercent(summary.accuracyTest, locale) : ''}
        />
        <KpiCard
          isLoading={summaryQuery.isLoading}
          label={t('admin.models.kpi.latency')}
          value={summary ? `${summary.meanLatencyMs} ms` : ''}
          hint="GPU T4 · batch 1"
        />
        <KpiCard
          isLoading={summaryQuery.isLoading}
          label={t('admin.models.kpi.storage')}
          value={summary ? `${summary.storageGb.toFixed(1)} GB` : ''}
          hint={summary ? t('admin.models.kpi.archivedVersions', { count: summary.archivedVersions }) : undefined}
        />
      </div>

      <Card>
        <CardContent className="pt-5">
          <div className="mb-4 flex items-center justify-between">
            <ToggleGroup
              type="single"
              value={statusFilter}
              onValueChange={(value) => value && setStatusFilter(value as ModelStatus | 'all')}
            >
              <ToggleGroupItem value="all">{t('admin.models.filters.allStatuses')}</ToggleGroupItem>
              <ToggleGroupItem value="production">{t('admin.models.status.production')}</ToggleGroupItem>
              <ToggleGroupItem value="archived">{t('admin.models.status.archived')}</ToggleGroupItem>
              <ToggleGroupItem value="validation">{t('admin.models.status.validation')}</ToggleGroupItem>
            </ToggleGroup>
            <span className="text-xs text-muted-foreground">{t('admin.models.filters.last12Months')}</span>
          </div>

          <ModelsTable
            models={filteredModels}
            onDeploy={(id) => deployMutation.mutate(id)}
            onRestore={(id) => revertMutation.mutate({ id, targetVersion: id })}
          />

          {modelsQuery.data && (
            <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground">
              <span>
                {t('admin.models.footer', {
                  shown: formatNumber(filteredModels.length, locale),
                  total: formatNumber(modelsQuery.data.length, locale),
                  archived: formatNumber(
                    modelsQuery.data.filter((model) => model.status === 'archived').length,
                    locale,
                  ),
                })}
              </span>
              <span>{t('admin.models.lastSync', { time: '08:41' })}</span>
            </div>
          )}
        </CardContent>
      </Card>
    </AdminShell>
  )
}
