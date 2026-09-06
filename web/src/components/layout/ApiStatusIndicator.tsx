import { Loader2, PlugZap, Unplug } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { useBackendStatus } from '@/hooks/useBackendStatus'
import { useI18n } from '@/i18n/I18nProvider'
import { cn } from '@/lib/utils'

/**
 * Estado real de la conexión con el backend.
 *
 * Antes mostraba una latencia inventada por un temporizador. Ahora refleja la
 * sonda de salud: qué origen alimenta la pantalla y con qué latencia medida.
 * Permite pulsar para reintentar la conexión.
 */
export function ApiStatusIndicator() {
  const { t, locale } = useI18n()
  const { estado, latenciaMs, info, comprobadoEn, revalidar } = useBackendStatus()

  const enLinea = estado === 'online'
  const comprobando = estado === 'checking'

  const etiquetaEstado = comprobando
    ? t('common.backend.checking')
    : enLinea
      ? t('common.backend.online')
      : t('common.backend.offline')

  const origen = enLinea ? t('common.backend.sourceApi') : t('common.backend.sourceMock')
  const version = info?.apiVersion ?? 'v2.4'

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          onClick={revalidar}
          aria-label={`${etiquetaEstado}. ${t('common.backend.retry')}`}
          className={cn(
            'hidden items-center gap-1.5 rounded-md px-1.5 py-1 text-xs text-muted-foreground transition-colors sm:flex',
            'outline-none hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring',
          )}
        >
          {comprobando ? (
            <Loader2 className="size-3 animate-spin" aria-hidden />
          ) : (
            <span className="relative flex size-2" aria-hidden>
              {enLinea && (
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-success-500 opacity-75" />
              )}
              <span
                className={cn(
                  'relative inline-flex size-2 rounded-full',
                  enLinea ? 'bg-success-500' : 'bg-warning-500',
                )}
              />
            </span>
          )}
          <span>API {version}</span>
          <span aria-hidden>·</span>
          <span className={cn(!enLinea && 'text-warning-600')}>
            {enLinea && latenciaMs !== null ? `${latenciaMs} ms` : origen}
          </span>
          {enLinea ? (
            <PlugZap className="size-3" aria-hidden />
          ) : (
            <Unplug className="size-3" aria-hidden />
          )}
        </button>
      </TooltipTrigger>
      <TooltipContent className="max-w-64">
        <p className="font-medium">{etiquetaEstado}</p>
        {info && <p className="text-muted-foreground">{info.appName} · {info.environment}</p>}
        {comprobadoEn !== null && (
          <p className="text-muted-foreground">
            {t('common.backend.lastCheck', {
              time: new Intl.DateTimeFormat(locale, {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              }).format(comprobadoEn),
            })}
          </p>
        )}
        <p className="mt-1">{t('common.backend.retry')}</p>
      </TooltipContent>
    </Tooltip>
  )
}
