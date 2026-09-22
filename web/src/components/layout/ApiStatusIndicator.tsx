import { ExternalLink, Loader2 } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { useBackendStatus } from '@/hooks/useBackendStatus'
import { useI18n } from '@/i18n/I18nProvider'
import { env } from '@/lib/env'
import { cn } from '@/lib/utils'

/**
 * Estado real de la conexión con el backend con hipervínculo a la documentación (/docs).
 *
 * Muestra la sonda de salud (versión y latencia) y enlaza directamente
 * con la documentación interactiva Swagger UI de la API de FastAPI.
 */
export function ApiStatusIndicator() {
  const { t, locale } = useI18n()
  const { estado, latenciaMs, info, comprobadoEn } = useBackendStatus()

  const enLinea = estado === 'online'
  const comprobando = estado === 'checking'

  const etiquetaEstado = comprobando
    ? t('common.backend.checking')
    : enLinea
      ? t('common.backend.online')
      : t('common.backend.offline')

  const origen = enLinea ? t('common.backend.sourceApi') : t('common.backend.sourceMock')
  const version = info?.apiVersion ?? 'v2.4'
  const docsUrl = `${env.apiBaseUrl || ''}/docs`

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <a
          href={docsUrl}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => {
            if (docsUrl) {
              window.open(docsUrl, '_blank', 'noopener,noreferrer')
              e.preventDefault()
            }
          }}
          aria-label={`${etiquetaEstado}. ${t('common.backend.docs')}`}
          className={cn(
            'group hidden cursor-pointer items-center gap-1.5 rounded-md px-1.5 py-1 text-xs text-muted-foreground transition-colors sm:flex',
            'outline-none hover:bg-accent hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring',
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
          <ExternalLink className="size-3 opacity-70 transition-transform group-hover:scale-110" aria-hidden />
        </a>
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
        <p className="mt-1 flex items-center gap-1 text-primary">
          <ExternalLink className="size-3" aria-hidden />
          <span>{t('common.backend.docs')}</span>
        </p>
      </TooltipContent>
    </Tooltip>
  )
}

