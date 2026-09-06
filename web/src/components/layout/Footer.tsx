import { useI18n } from '@/i18n/I18nProvider'

export function Footer() {
  const { t } = useI18n()

  return (
    <footer className="border-t border-border">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-2 px-4 py-4 text-xs text-muted-foreground sm:flex-row sm:px-6">
        <p>{t('common.disclaimer')}</p>
        <p>{t('common.datasetCredit')}</p>
      </div>
    </footer>
  )
}
