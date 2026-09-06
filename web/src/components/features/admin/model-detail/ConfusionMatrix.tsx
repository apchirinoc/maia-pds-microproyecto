import { useI18n } from '@/i18n/I18nProvider'
import { cn } from '@/lib/utils'
import { lerpColor } from '@/lib/geo'
import { TUMOR_CLASSES } from '@/types/classification'
import type { ConfusionMatrix as ConfusionMatrixData } from '@/types/model'

export interface ConfusionMatrixProps {
  matrix: ConfusionMatrixData
}

export function ConfusionMatrix({ matrix }: ConfusionMatrixProps) {
  const { t } = useI18n()

  const maxValue = Math.max(
    ...TUMOR_CLASSES.flatMap((row) => TUMOR_CLASSES.map((col) => matrix[row][col])),
  )

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            <th className="p-2" />
            {TUMOR_CLASSES.map((col) => (
              <th key={col} className="p-2 text-center text-xs font-medium text-muted-foreground">
                {t(`classes.${col}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {TUMOR_CLASSES.map((row) => (
            <tr key={row}>
              <th className="whitespace-nowrap p-2 text-right text-xs font-medium text-muted-foreground">
                {t(`classes.${row}`)}
              </th>
              {TUMOR_CLASSES.map((col) => {
                const value = matrix[row][col]
                const isDiagonal = row === col
                const intensity = maxValue > 0 ? value / maxValue : 0
                return (
                  <td key={col} className="p-1">
                    <div
                      className={cn(
                        'flex size-14 items-center justify-center rounded-md text-sm font-semibold',
                        isDiagonal ? 'text-white' : 'text-foreground',
                      )}
                      style={{
                        backgroundColor: isDiagonal
                          ? lerpColor('#c7d2fe', '#3730a3', intensity)
                          : lerpColor('#f4f4f5', '#d4d4d8', intensity),
                      }}
                    >
                      {value}
                    </div>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
