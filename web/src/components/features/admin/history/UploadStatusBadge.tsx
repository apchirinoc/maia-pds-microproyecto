import { Badge } from '@/components/ui/badge'
import { useI18n } from '@/i18n/I18nProvider'
import type { UploadStatus } from '@/types/upload'

const VARIANT_BY_STATUS: Record<UploadStatus, 'success' | 'warning' | 'danger'> = {
  validated: 'success',
  pending: 'warning',
  discarded: 'danger',
}

export function UploadStatusBadge({ status }: { status: UploadStatus }) {
  const { t } = useI18n()
  return <Badge variant={VARIANT_BY_STATUS[status]}>{t(`admin.history.status.${status}`)}</Badge>
}
