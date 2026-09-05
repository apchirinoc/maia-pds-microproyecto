import { Activity, FlaskConical } from 'lucide-react'
import { useI18n } from '@/i18n/I18nProvider'

export function AuthSplitPanel() {
  const { t } = useI18n()

  return (
    <div className="relative hidden flex-col justify-between overflow-hidden bg-brand-900 p-10 text-brand-50 lg:flex">
      <div className="flex items-center gap-2 font-semibold">
        <Activity className="size-5" aria-hidden />
        {t('common.appName')}
      </div>

      <div className="max-w-sm">
        <h2 className="text-2xl font-semibold leading-snug">{t('auth.brandTitle')}</h2>
        <p className="mt-3 text-sm text-brand-200">{t('auth.brandSubtitle')}</p>
      </div>

      {/*
        Aviso de estado real del proyecto. Sustituye a los distintivos
        «ISO 13485 · HIPAA-ready · GDPR», que afirmaban un cumplimiento sin
        ningún control que lo respaldara. Ver docs/gobierno/evaluacion-riesgo-modelo.md
        (riesgos R-02 y R-06): afirmar conformidad sin evidencia es en sí mismo
        un riesgo de gobierno. No reintroducir sin un documento que lo sustente.
      */}
      <div
        role="note"
        className="flex max-w-sm items-start gap-2 border-t border-brand-800 pt-4 text-xs leading-relaxed text-brand-200 dark:border-brand-700 dark:text-brand-100"
      >
        <FlaskConical className="mt-0.5 size-4 shrink-0" aria-hidden />
        <p>{t('auth.researchNotice')}</p>
      </div>

      <svg
        className="pointer-events-none absolute -right-24 -top-24 size-96 text-brand-800 opacity-40"
        viewBox="0 0 200 200"
        aria-hidden
      >
        <path
          fill="currentColor"
          d="M100 20c-40 0-60 30-60 65 0 30 15 55 35 70 5 15 15 25 25 25s20-10 25-25c20-15 35-40 35-70 0-35-20-65-60-65Z"
        />
      </svg>
    </div>
  )
}
