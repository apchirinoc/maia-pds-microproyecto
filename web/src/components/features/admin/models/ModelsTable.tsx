import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useI18n } from '@/i18n/I18nProvider'
import { formatPercent } from '@/lib/format'
import type { DeployedModel } from '@/types/model'
import { ModelStatusBadge } from './ModelStatusBadge'

export interface ModelsTableProps {
  models: DeployedModel[]
  onDeploy: (id: string) => void
  onRestore: (id: string) => void
}

const SECONDARY_ACTION: Record<DeployedModel['status'], 'retrain' | 'restore' | 'deploy' | 'compare' | null> = {
  production: 'retrain',
  archived: 'restore',
  validation: 'deploy',
  baseline: 'compare',
}

export function ModelsTable({ models, onDeploy, onRestore }: ModelsTableProps) {
  const { t, locale } = useI18n()
  const navigate = useNavigate()

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t('admin.models.table.model')}</TableHead>
          <TableHead>{t('admin.models.table.architecture')}</TableHead>
          <TableHead>{t('admin.models.table.accuracy')}</TableHead>
          <TableHead>{t('admin.models.table.f1')}</TableHead>
          <TableHead>{t('admin.models.table.size')}</TableHead>
          <TableHead>{t('admin.models.table.status')}</TableHead>
          <TableHead className="text-right">{t('admin.models.table.actions')}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {models.map((model) => {
          const secondaryAction = SECONDARY_ACTION[model.status]
          return (
            <TableRow key={model.id}>
              <TableCell>
                <div className="font-medium">
                  {model.name} {model.version}
                </div>
                <div className="text-xs text-muted-foreground">{model.weightsFileName}</div>
              </TableCell>
              <TableCell className="text-muted-foreground">{model.architecture}</TableCell>
              <TableCell className="tabular-nums">{formatPercent(model.accuracy, locale, 1)}</TableCell>
              <TableCell className="tabular-nums">{model.f1.toFixed(3)}</TableCell>
              <TableCell className="text-muted-foreground">
                {model.sizeMb >= 1024 ? `${(model.sizeMb / 1024).toFixed(1)} GB` : `${model.sizeMb} MB`}
              </TableCell>
              <TableCell>
                <ModelStatusBadge status={model.status} />
              </TableCell>
              <TableCell className="text-right">
                <div className="flex justify-end gap-2">
                  <Button variant="outline" size="sm" onClick={() => navigate(`/admin/models/${model.id}`)}>
                    {t('admin.models.table.detail')}
                  </Button>
                  {secondaryAction && (
                    <Button
                      size="sm"
                      variant={secondaryAction === 'deploy' ? 'default' : 'outline'}
                      onClick={() => {
                        if (secondaryAction === 'deploy') onDeploy(model.id)
                        if (secondaryAction === 'restore') onRestore(model.id)
                      }}
                    >
                      {t(`admin.models.table.${secondaryAction}`)}
                    </Button>
                  )}
                </div>
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
