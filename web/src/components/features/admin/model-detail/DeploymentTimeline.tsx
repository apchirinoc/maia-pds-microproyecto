import { useI18n } from '@/i18n/I18nProvider'
import { formatDate } from '@/lib/format'
import type { DeploymentEvent } from '@/types/model'

export function DeploymentTimeline({ events }: { events: DeploymentEvent[] }) {
  const { t, locale } = useI18n()

  return (
    <ol className="flex flex-col gap-4">
      {events.map((event, index) => (
        <li key={event.id} className="relative flex gap-3 pl-1">
          <div className="flex flex-col items-center">
            <span className="mt-1 size-2 shrink-0 rounded-full bg-primary" aria-hidden />
            {index < events.length - 1 && <span className="mt-1 w-px flex-1 bg-border" aria-hidden />}
          </div>
          <div className="pb-2">
            <p className="text-sm font-medium">{t(`admin.modelDetail.timeline.${event.label}`)}</p>
            <p className="text-xs text-muted-foreground">
              {formatDate(event.date, locale)} · {event.author}
            </p>
          </div>
        </li>
      ))}
    </ol>
  )
}
