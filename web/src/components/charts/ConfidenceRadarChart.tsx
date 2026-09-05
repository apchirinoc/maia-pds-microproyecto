import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import { useI18n } from '@/i18n/I18nProvider'
import { CHART_GRID_COLOR, CHART_MUTED_COLOR, TUMOR_CLASS_COLORS } from '@/lib/tumor-class-colors'
import type { RecentUploadsProfilePoint } from '@/mocks/dashboard.mock'

export interface ConfidenceRadarChartProps {
  data: RecentUploadsProfilePoint[]
}

const AXIS_COLORS: Record<string, string> = {
  glioma: TUMOR_CLASS_COLORS.glioma ?? '#4f46e5',
  meningioma: TUMOR_CLASS_COLORS.meningioma ?? '#059669',
  pituitary: TUMOR_CLASS_COLORS.pituitary ?? '#d97706',
  healthy: TUMOR_CLASS_COLORS.healthy ?? '#0891b2',
  confidence: '#8b5cf6',
  volume: '#2563eb',
}

interface RadarChartItem {
  axis: string
  rawAxis: string
  value: number
  color: string
  category: 'metric' | 'class'
}

interface TooltipPayloadEntry {
  value?: number
  payload?: RadarChartItem
}

interface CustomRadarTooltipProps {
  active?: boolean
  payload?: TooltipPayloadEntry[]
  t: (key: string) => string
}

function RadarCustomTooltip({ active, payload, t }: CustomRadarTooltipProps) {
  if (!active || !payload || !payload.length) return null
  const data = payload[0]?.payload
  if (!data) return null

  const categoryLabel =
    data.category === 'metric'
      ? t('dashboard.recentProfile.metric')
      : t('dashboard.recentProfile.tumorClass')

  return (
    <div className="pointer-events-none z-50 min-w-40 rounded-xl border border-border bg-popover/95 p-3 text-xs shadow-xl backdrop-blur-md transition-all duration-150">
      <div className="mb-2 flex items-center justify-between gap-2 border-b border-border/60 pb-2">
        <div className="flex items-center gap-2">
          <span
            className="size-2.5 shrink-0 rounded-full ring-2 ring-background"
            style={{ backgroundColor: data.color }}
          />
          <span className="font-semibold text-foreground">{data.axis}</span>
        </div>
        <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          {categoryLabel}
        </span>
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-muted-foreground">
          <span>{t('dashboard.recentProfile.score')}</span>
          <span className="text-sm font-bold tabular-nums text-foreground">
            {data.value}%
          </span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full transition-all duration-500 ease-out"
            style={{
              width: `${Math.min(100, Math.max(0, data.value))}%`,
              backgroundColor: data.color,
            }}
          />
        </div>
      </div>
    </div>
  )
}

function renderRadarDot(props: any) {
  const { cx, cy, payload, index } = props
  if (cx == null || cy == null) return null
  const color = payload?.color || '#4f46e5'

  return (
    <circle
      key={`radar-dot-${index}`}
      cx={cx}
      cy={cy}
      r={4}
      fill={color}
      stroke="var(--card, #ffffff)"
      strokeWidth={2}
    />
  )
}

function renderRadarActiveDot(props: any) {
  const { cx, cy, payload, index } = props
  if (cx == null || cy == null) return null
  const color = payload?.color || '#4f46e5'

  return (
    <g key={`radar-active-dot-${index}`}>
      <circle
        cx={cx}
        cy={cy}
        r={11}
        fill={color}
        fillOpacity={0.25}
      />
      <circle
        cx={cx}
        cy={cy}
        r={5.5}
        fill={color}
        stroke="#ffffff"
        strokeWidth={2}
      />
    </g>
  )
}

export function ConfidenceRadarChart({ data }: ConfidenceRadarChartProps) {
  const { t } = useI18n()

  const chartData: RadarChartItem[] = data.map((point) => ({
    axis:
      point.axis === 'confidence'
        ? t('dashboard.recentProfile.confidence')
        : point.axis === 'volume'
          ? t('dashboard.recentProfile.volume')
          : t(`classes.${point.axis}`),
    rawAxis: point.axis,
    value: point.value,
    color: AXIS_COLORS[point.axis] ?? '#4f46e5',
    category: point.axis === 'confidence' || point.axis === 'volume' ? 'metric' : 'class',
  }))

  return (
    <ResponsiveContainer width="100%" height="100%">
      <RadarChart data={chartData} outerRadius="66%" margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
        <defs>
          <radialGradient id="radarProfileGradient" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#6366f1" stopOpacity={0.45} />
            <stop offset="100%" stopColor="#4f46e5" stopOpacity={0.15} />
          </radialGradient>
        </defs>
        <PolarGrid stroke={CHART_GRID_COLOR} />
        <PolarAngleAxis
          dataKey="axis"
          tick={{ fill: CHART_MUTED_COLOR, fontSize: 10.5, fontWeight: 500 }}
        />
        <PolarRadiusAxis domain={[0, 100]} axisLine={false} tick={false} />
        <Tooltip
          content={<RadarCustomTooltip t={t} />}
          cursor={{
            stroke: '#6366f1',
            strokeWidth: 1.5,
            strokeDasharray: '3 3',
            strokeOpacity: 0.45,
          }}
        />
        <Radar
          name={t('dashboard.recentProfile.title')}
          dataKey="value"
          stroke="#4f46e5"
          strokeWidth={2}
          fill="url(#radarProfileGradient)"
          dot={renderRadarDot}
          activeDot={renderRadarActiveDot}
          // Sin animación de entrada, igual que el donut y el gráfico de barras.
          // La animación depende de `requestAnimationFrame`; si el navegador la
          // limita (pestaña en segundo plano, render sin foco) el polígono se
          // queda congelado en su fotograma inicial, con todos los vértices en
          // el centro, y la gráfica aparece vacía.
          isAnimationActive={false}
        />
      </RadarChart>
    </ResponsiveContainer>
  )
}
