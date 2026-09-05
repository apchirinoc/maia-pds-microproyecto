import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useI18n } from '@/i18n/I18nProvider'
import { TUMOR_CLASSES, type TumorClass } from '@/types/classification'

export interface ClassFilterTabsProps {
  value: TumorClass | 'all'
  onValueChange: (value: TumorClass | 'all') => void
}

export function ClassFilterTabs({ value, onValueChange }: ClassFilterTabsProps) {
  const { t } = useI18n()

  return (
    <Tabs value={value} onValueChange={(next) => onValueChange(next as TumorClass | 'all')}>
      <TabsList>
        <TabsTrigger value="all">{t('admin.history.filters.all')}</TabsTrigger>
        {TUMOR_CLASSES.map((tumorClass) => (
          <TabsTrigger key={tumorClass} value={tumorClass}>
            {t(`classes.${tumorClass}`)}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  )
}
