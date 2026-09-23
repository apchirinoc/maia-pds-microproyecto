import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useActivateRegistryVersion, useRegistryVersions } from '@/hooks/useModels'
import { useI18n } from '@/i18n/I18nProvider'

export interface RegistryModelPickerProps {
  /** Se invoca tras activar una versión (por ejemplo, para cerrar un diálogo). */
  onActivated?: () => void
}

/**
 * Reemplaza la subida de un archivo de pesos por la SELECCIÓN de una versión ya
 * versionada en el Model Registry (S3/MLflow). Activar una versión fija el alias
 * `champion`; a partir de ahí la API la sirve desde S3.
 */
export function RegistryModelPicker({ onActivated }: RegistryModelPickerProps) {
  const { t } = useI18n()
  const versionsQuery = useRegistryVersions()
  const activateMutation = useActivateRegistryVersion()

  async function handleActivate(version: string) {
    await activateMutation.mutateAsync(version)
    onActivated?.()
  }

  return (
    <div>
      <p className="mb-1 text-sm font-medium">{t('admin.modelDetail.registryPicker.title')}</p>
      <p className="mb-3 text-xs text-muted-foreground">
        {t('admin.modelDetail.registryPicker.subtitle')}
      </p>

      <p className="mb-3 text-xs">El alias del registro no cambia el motor en ejecución. La versión se fija al desplegar la API.</p>
      {versionsQuery.isError && <p role="alert">No se pudo consultar MLflow. <button onClick={() => versionsQuery.refetch()} className="underline">Reintentar</button></p>}
      {versionsQuery.isLoading && <Skeleton className="h-24 w-full" />}

      {versionsQuery.data && versionsQuery.data.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No hay versiones disponibles en esta conexión.
        </p>
      )}

      <ul className="flex flex-col gap-2">
        {versionsQuery.data?.map((version) => {
          const isChampion = version.alias === 'champion'
          const isActivating =
            activateMutation.isPending && activateMutation.variables === version.version
          return (
            <li
              key={version.version}
              className="flex items-center justify-between gap-3 rounded-lg border border-border p-3"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium">v{version.version}</span>
                  <span className="truncate text-xs text-muted-foreground">{version.arch}</span>
                  {isChampion && (
                    <Badge variant="success">
                      {t('admin.modelDetail.registryPicker.champion')}
                    </Badge>
                  )}
                </div>
                <p className="mt-0.5 text-xs tabular-nums text-muted-foreground">
                  {t('admin.modelDetail.registryPicker.metrics')}: {version.f1?.toFixed(3) ?? '—'} ·{' '}
                  {version.recall?.toFixed(3) ?? '—'}
                </p>
              </div>
              <Button
                size="sm"
                variant={isChampion ? 'outline' : 'default'}
                disabled
                title="La versión se configura al desplegar la API."
                onClick={() => handleActivate(version.version)}
              >
                {isActivating
                  ? t('admin.modelDetail.registryPicker.activating')
                  : isChampion
                    ? t('admin.modelDetail.registryPicker.champion')
                    : t('admin.modelDetail.registryPicker.activate')}
              </Button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
