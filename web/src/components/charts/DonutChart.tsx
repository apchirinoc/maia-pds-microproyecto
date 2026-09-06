import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { useI18n } from '@/i18n/I18nProvider'
import { TUMOR_CLASS_COLORS } from '@/lib/tumor-class-colors'
import type { TumorClass } from '@/types/classification'
import { formatNumber } from '@/lib/format'

export interface DonutChartProps {
  data: Record<TumorClass, number>
}

export function DonutChart({ data }: DonutChartProps) {
  const { t, locale } = useI18n()
  const entries = (Object.entries(data) as [TumorClass, number][]).map(([tumorClass, value]) => ({
    tumorClass,
    value,
    label: t(`classes.${tumorClass}`),
  }))
  const total = entries.reduce((sum, entry) => sum + entry.value, 0)

  return (
    <div className="flex size-full min-h-0 flex-col">
      <div className="relative min-h-0 flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={entries}
              dataKey="value"
              nameKey="label"
              innerRadius="66%"
              outerRadius="92%"
              paddingAngle={2}
              stroke="none"
              isAnimationActive={false}
            >
              {entries.map((entry) => (
                <Cell key={entry.tumorClass} fill={TUMOR_CLASS_COLORS[entry.tumorClass]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => formatNumber(Number(value), locale)}
              contentStyle={{
                background: 'var(--popover)',
                border: '1px solid var(--border)',
                borderRadius: 8,
                fontSize: 12,
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xl font-semibold tabular-nums">{formatNumber(total, locale)}</span>
          <span className="text-[11px] text-muted-foreground">
            {t('dashboard.trainingDistribution.centerLabel')}
          </span>
        </div>
      </div>

      <ul className="mt-3 grid shrink-0 grid-cols-2 gap-x-3 gap-y-1.5 text-xs">
        {entries.map((entry) => (
          <li key={entry.tumorClass} className="flex min-w-0 items-center gap-1.5">
            <span
              className="size-2 shrink-0 rounded-full"
              style={{ backgroundColor: TUMOR_CLASS_COLORS[entry.tumorClass] }}
              aria-hidden
            />
            <span className="truncate text-muted-foreground">{entry.label}</span>
            <span className="ml-auto shrink-0 font-medium tabular-nums">
              {formatNumber(entry.value, locale)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
