import { Bar, Cell, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useI18n } from '@/i18n/I18nProvider'
import { formatNumber } from '@/lib/format'
import { lerpColor } from '@/lib/geo'
import { CHART_MUTED_COLOR } from '@/lib/tumor-class-colors'

const BAR_COLOR_LOW = '#c7d2fe'
const BAR_COLOR_HIGH = '#4338ca'
const TREND_COLOR = '#10b981'

export interface MonthlyBarChartProps {
  data: { month: string; uploads: number }[]
}

export function MonthlyBarChart({ data }: MonthlyBarChartProps) {
  const { locale } = useI18n()
  const maxUploads = Math.max(1, ...data.map((point) => point.uploads))
  const chartData = data.map((point, index) => ({ ...point, key: `${point.month}-${index}` }))

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={chartData} margin={{ top: 6, right: 4, bottom: 0, left: -28 }}>
        <XAxis
          dataKey="month"
          axisLine={false}
          tickLine={false}
          tick={{ fill: CHART_MUTED_COLOR, fontSize: 10 }}
        />
        <YAxis hide domain={[0, maxUploads * 1.1]} />
        <Tooltip
          cursor={{ fill: 'var(--muted)' }}
          formatter={(value) => formatNumber(Number(value), locale)}
          contentStyle={{
            background: 'var(--popover)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Bar dataKey="uploads" radius={[3, 3, 0, 0]} maxBarSize={18} isAnimationActive={false}>
          {chartData.map((point) => (
            <Cell
              key={point.key}
              fill={lerpColor(BAR_COLOR_LOW, BAR_COLOR_HIGH, point.uploads / maxUploads)}
            />
          ))}
        </Bar>
        <Line
          type="monotone"
          dataKey="uploads"
          stroke={TREND_COLOR}
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
