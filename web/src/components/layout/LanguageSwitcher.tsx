import { useI18n } from '@/i18n/I18nProvider'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import type { Locale } from '@/i18n/dictionaries'

export function LanguageSwitcher() {
  const { locale, setLocale } = useI18n()

  return (
    <ToggleGroup
      type="single"
      value={locale}
      onValueChange={(value) => value && setLocale(value as Locale)}
      aria-label="Language"
    >
      <ToggleGroupItem value="es" aria-label="Español">
        ES
      </ToggleGroupItem>
      <ToggleGroupItem value="en" aria-label="English">
        EN
      </ToggleGroupItem>
    </ToggleGroup>
  )
}
