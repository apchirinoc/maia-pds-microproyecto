import { MapPin } from 'lucide-react'
import { useMemo } from 'react'
import { ComposableMap, Geographies, Geography, Marker } from 'react-simple-maps'
import worldAtlas from 'world-atlas/countries-110m.json'
import { COUNTRIES } from '@/mocks/countries.mock'
import { cn } from '@/lib/utils'

const WORLD_TOPOJSON = worldAtlas as unknown as Parameters<typeof Geographies>[0]['geography']

export interface CountryPickerMapProps {
  selectedCountryCode: string | null
  onSelectCountry: (countryCode: string | null, countryName?: string) => void
}

export function CountryPickerMap({ selectedCountryCode, onSelectCountry }: CountryPickerMapProps) {
  const countryByName = useMemo(() => {
    const map = new Map<string, (typeof COUNTRIES)[number]>()
    for (const country of COUNTRIES) map.set(country.name, country)
    return map
  }, [])

  const selectedCountry = COUNTRIES.find((country) => country.code === selectedCountryCode)

  return (
    <ComposableMap
      projection="geoEqualEarth"
      projectionConfig={{ scale: 130 }}
      className="w-full"
      style={{ width: '100%', height: 'auto' }}
    >
      <Geographies geography={WORLD_TOPOJSON}>
        {({ geographies }) =>
          geographies.map((geography) => {
            const name = geography.properties.name as string
            const country = countryByName.get(name)
            const isSelected = country?.code === selectedCountryCode
            const isSelectable = Boolean(country)

            return (
              <Geography
                key={geography.rsmKey}
                geography={geography}
                onClick={() => {
                  if (country) {
                    if (isSelected) {
                      onSelectCountry(null)
                    } else {
                      onSelectCountry(country.code, country.name)
                    }
                  }
                }}
                fill={isSelected ? '#4338ca' : 'var(--muted)'}
                stroke="var(--background)"
                strokeWidth={0.5}
                className={cn(isSelectable && 'cursor-pointer')}
                style={{
                  default: { outline: 'none' },
                  hover: {
                    outline: 'none',
                    fill: isSelected ? '#3730a3' : isSelectable ? '#818cf8' : 'var(--muted)',
                  },
                  pressed: { outline: 'none', fill: '#4338ca' },
                }}
              />
            )
          })
        }
      </Geographies>

      {selectedCountry && (
        <Marker
          coordinates={[selectedCountry.longitude, selectedCountry.latitude]}
          className="cursor-pointer"
          onClick={() => onSelectCountry(null)}
        >
          <MapPin
            className="-translate-x-1/2 -translate-y-full transition-transform hover:scale-125"
            size={22}
            color="#dc2626"
            fill="#fecaca"
          />
        </Marker>
      )}
    </ComposableMap>
  )
}
