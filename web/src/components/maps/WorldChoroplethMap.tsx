import { geoCentroid } from 'd3-geo'
import { useMemo } from 'react'
import { ComposableMap, Geographies, Geography, Marker } from 'react-simple-maps'
import worldAtlas from 'world-atlas/countries-110m.json'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { useI18n } from '@/i18n/I18nProvider'
import { formatNumber } from '@/lib/format'
import { lerpColor, logScale, sqrtRadius } from '@/lib/geo'
import type { CountryUploadStat } from '@/types/country'

const WORLD_TOPOJSON = worldAtlas as unknown as Parameters<typeof Geographies>[0]['geography']
const COLOR_LOW = '#e0e7ff'
const COLOR_HIGH = '#4338ca'

export interface WorldChoroplethMapProps {
  data: CountryUploadStat[]
  mode: 'choropleth' | 'bubbles'
}

export function WorldChoroplethMap({ data, mode }: WorldChoroplethMapProps) {
  const { locale } = useI18n()

  const byName = useMemo(() => {
    const map = new Map<string, CountryUploadStat>()
    for (const stat of data) map.set(stat.countryName, stat)
    return map
  }, [data])

  const maxUploads = useMemo(() => Math.max(1, ...data.map((stat) => stat.uploads)), [data])

  return (
    <TooltipProvider delayDuration={150}>
      <div className="size-full min-h-0">
        <ComposableMap
          projection="geoEqualEarth"
          projectionConfig={{ scale: 170 }}
          width={880}
          height={440}
          style={{ width: '100%', height: '100%' }}
        >
          <Geographies geography={WORLD_TOPOJSON}>
            {({ geographies }) =>
              geographies.map((geography) => {
                const name = geography.properties.name as string
                const stat = byName.get(name)
                const fill =
                  mode === 'choropleth' && stat
                    ? lerpColor(COLOR_LOW, COLOR_HIGH, logScale(stat.uploads, maxUploads))
                    : 'var(--muted)'

                return (
                  <Tooltip key={geography.rsmKey}>
                    <TooltipTrigger asChild>
                      <Geography
                        geography={geography}
                        fill={fill}
                        stroke="var(--background)"
                        strokeWidth={0.5}
                        style={{
                          default: { outline: 'none' },
                          hover: { outline: 'none', fill: '#6366f1' },
                          pressed: { outline: 'none' },
                        }}
                      />
                    </TooltipTrigger>
                    <TooltipContent>
                      {name}
                      {stat ? ` · ${formatNumber(stat.uploads, locale)}` : ''}
                    </TooltipContent>
                  </Tooltip>
                )
              })
            }
          </Geographies>

          {mode === 'bubbles' && (
            <Geographies geography={WORLD_TOPOJSON}>
              {({ geographies }) =>
                geographies.map((geography) => {
                  const name = geography.properties.name as string
                  const stat = byName.get(name)
                  if (!stat) return null
                  const centroid = geoCentroid(geography)
                  if (!Number.isFinite(centroid[0]) || !Number.isFinite(centroid[1])) return null

                  return (
                    <Tooltip key={`bubble-${geography.rsmKey}`}>
                      <TooltipTrigger asChild>
                        <Marker coordinates={centroid}>
                          <circle
                            r={sqrtRadius(stat.uploads, maxUploads)}
                            fill="#4338ca"
                            fillOpacity={0.55}
                            stroke="#4338ca"
                            strokeWidth={1}
                          />
                        </Marker>
                      </TooltipTrigger>
                      <TooltipContent>
                        {name} · {formatNumber(stat.uploads, locale)}
                      </TooltipContent>
                    </Tooltip>
                  )
                })
              }
            </Geographies>
          )}
        </ComposableMap>
      </div>
    </TooltipProvider>
  )
}

export function ChoroplethScale({ minLabel, maxLabel }: { minLabel: string; maxLabel: string }) {
  return (
    <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
      <span>{minLabel}</span>
      <span
        className="h-2 w-24 rounded-full"
        style={{ background: `linear-gradient(to right, ${COLOR_LOW}, ${COLOR_HIGH})` }}
        aria-hidden
      />
      <span>{maxLabel}</span>
    </div>
  )
}
