import { ArrowLeft, Download } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { AdminShell } from '@/components/layout/AdminShell'
import { ConfusionMatrix } from '@/components/features/admin/model-detail/ConfusionMatrix'
import { ClassPerformanceList } from '@/components/features/admin/model-detail/ClassPerformanceList'
import { DeploymentTimeline } from '@/components/features/admin/model-detail/DeploymentTimeline'
import { RegistryModelPicker } from '@/components/features/admin/model-detail/RegistryModelPicker'
import { ModelStatusBadge } from '@/components/features/admin/models/ModelStatusBadge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useI18n } from '@/i18n/I18nProvider'
import { useModelDetail, useRevertModel } from '@/hooks/useModels'

export function ModelDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { t } = useI18n()
  const navigate = useNavigate()
  const modelQuery = useModelDetail(id)
  const revertMutation = useRevertModel()

  const model = modelQuery.data

  async function handleConfirmRevert() {
    if (!model?.previousVersion) return
    await revertMutation.mutateAsync({ id: model.id, targetVersion: model.previousVersion })
    navigate('/admin/models')
  }

  if (modelQuery.isError) {
    return <AdminShell><p role="alert">No se pudo consultar el modelo.</p><Button onClick={() => modelQuery.refetch()}>Reintentar</Button></AdminShell>
  }

  if (modelQuery.isLoading || !model) {
    return (
      <AdminShell>
        <Skeleton className="h-8 w-64" />
        <Skeleton className="mt-4 h-64 w-full" />
      </AdminShell>
    )
  }

  return (
    <AdminShell>
      <Link
        to="/admin/models"
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
      >
        <ArrowLeft className="size-4" /> {t('admin.modelDetail.back')}
      </Link>

      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 flex-wrap items-center gap-3">
          <h1 className="min-w-0 break-words text-2xl font-semibold">
            {model.name} {model.version}
          </h1>
          {model.dataSource === 'artifact' && model.status === 'production' && (
            <Badge variant="success">{t('admin.modelDetail.inProduction')}</Badge>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" disabled title="Obtenga el paquete desde el almacén de artefactos indicado en el manual de instalación.">
            <Download /> {t('admin.modelDetail.downloadWeights')}
          </Button>
          {model.previousVersion && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" disabled title="La versión se configura al desplegar la API.">
                  {t('admin.modelDetail.revertTo', { version: model.previousVersion.replace(/^v/, '') })}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>
                    {t('admin.modelDetail.revertConfirmTitle', {
                      version: model.previousVersion.replace(/^v/, ''),
                    })}
                  </AlertDialogTitle>
                  <AlertDialogDescription>{t('admin.modelDetail.revertConfirmBody')}</AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
                  <AlertDialogAction onClick={handleConfirmRevert}>{t('common.confirm')}</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>
      </div>

      <p className="mb-4 text-sm">{model.dataSource === 'artifact' ? 'Métricas registradas del modelo. — indica un dato no disponible.' : 'Este registro contiene información de referencia.'}</p>
      <div className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetricTile label={t('admin.modelDetail.metrics.accuracy')} value={model.metrics.accuracy == null ? '—' : `${model.metrics.accuracy}%`} />
        <MetricTile label={t('admin.modelDetail.metrics.precision')} value={model.metrics.precisionMacro?.toFixed(3) ?? '—'} />
        <MetricTile label={t('admin.modelDetail.metrics.recall')} value={model.metrics.recallMacro?.toFixed(3) ?? '—'} />
        <MetricTile label={t('admin.modelDetail.metrics.auc')} value={model.metrics.auc?.toFixed(3) ?? '—'} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>{t('admin.modelDetail.confusionMatrix.title')}</CardTitle>
            <p className="text-xs text-muted-foreground">
              {model.testImages > 0 ? t('admin.modelDetail.confusionMatrix.subtitle', { count: model.testImages }) : 'Tamaño del conjunto de evaluación no disponible.'}
            </p>
          </CardHeader>
          <CardContent>
            <ConfusionMatrix matrix={model.confusionMatrix} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <ModelStatusBadge status={model.status} />
          </CardHeader>
          <CardContent>
            <RegistryModelPicker />
          </CardContent>
        </Card>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t('admin.modelDetail.classPerformance')}</CardTitle>
          </CardHeader>
          <CardContent>
            <ClassPerformanceList performance={model.classPerformance} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('admin.modelDetail.deploymentHistory')}</CardTitle>
          </CardHeader>
          <CardContent>
            <DeploymentTimeline events={model.deploymentHistory} />
          </CardContent>
        </Card>
      </div>
    </AdminShell>
  )
}

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-semibold tabular-nums">{value}</p>
    </div>
  )
}
