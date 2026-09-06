import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { dictionaries, type Locale } from './dictionaries'

interface I18nContextValue {
  locale: Locale
  setLocale: (locale: Locale) => void
  t: (key: string, vars?: Record<string, string | number>) => string
}

const STORAGE_KEY = 'brainneuroscan.locale'
const SUPPORTED_LOCALES: Locale[] = ['es', 'en']

const I18nContext = createContext<I18nContextValue | null>(null)

function readStoredLocale(): Locale {
  if (typeof window === 'undefined') return 'es'
  const stored = window.localStorage.getItem(STORAGE_KEY)
  if (stored === 'es' || stored === 'en') return stored
  const browserLang = window.navigator.language.slice(0, 2)
  return SUPPORTED_LOCALES.includes(browserLang as Locale) ? (browserLang as Locale) : 'es'
}

function resolvePath(source: unknown, path: string[]): unknown {
  return path.reduce<unknown>((acc, segment) => {
    if (acc && typeof acc === 'object' && segment in acc) {
      return (acc as Record<string, unknown>)[segment]
    }
    return undefined
  }, source)
}

function interpolate(template: string, vars?: Record<string, string | number>): string {
  if (!vars) return template
  return template.replace(/\{\{(\w+)\}\}/g, (match, key: string) =>
    key in vars ? String(vars[key]) : match,
  )
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => readStoredLocale())

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next)
    window.localStorage.setItem(STORAGE_KEY, next)
    window.document.documentElement.lang = next
  }, [])

  const t = useCallback(
    (key: string, vars?: Record<string, string | number>) => {
      const value = resolvePath(dictionaries[locale], key.split('.'))
      if (typeof value !== 'string') {
        if (import.meta.env.DEV) {
          console.warn(`[i18n] Missing key "${key}" for locale "${locale}"`)
        }
        return key
      }
      return interpolate(value, vars)
    },
    [locale],
  )

  const value = useMemo<I18nContextValue>(() => ({ locale, setLocale, t }), [locale, setLocale, t])

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used within an I18nProvider')
  return ctx
}
