import type { ReactNode } from 'react'
import { useI18n } from '@/i18n/I18nProvider'

export function AdminShell({ children }: { children: ReactNode }) {
  const { t } = useI18n()

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {t('admin.breadcrumb')}
      </p>
      {children}
    </div>
  )
}
