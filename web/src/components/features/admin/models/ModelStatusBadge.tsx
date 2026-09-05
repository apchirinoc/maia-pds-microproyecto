import { Badge } from '@/components/ui/badge'
import { useI18n } from '@/i18n/I18nProvider'
import type { ModelStatus } from '@/types/model'

const VARIANT_BY_STATUS: Record<ModelStatus, 'success' | 'neutral' | 'warning' | 'info'> = {
  production: 'success',
  archived: 'neutral',
  validation: 'warning',
  baseline: 'info',
}

export function ModelStatusBadge({ status }: { status: ModelStatus }) {
  const { t } = useI18n()
  return <Badge variant={VARIANT_BY_STATUS[status]}>{t(`admin.models.status.${status}`)}</Badge>
}
