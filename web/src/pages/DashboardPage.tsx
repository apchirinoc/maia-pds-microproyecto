import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { KpiCard } from '@/components/features/dashboard/KpiCard'
import { ChartCard } from '@/components/features/dashboard/ChartCard'
import {
  DatasetSampleGallery,
  KaggleLink,
} from '@/components/features/dashboard/DatasetSampleGallery'
import { DonutChart } from '@/components/charts/DonutChart'
import { MonthlyBarChart } from '@/components/charts/MonthlyBarChart'
import { ConfidenceRadarChart } from '@/components/charts/ConfidenceRadarChart'
import { ChoroplethScale, WorldChoroplethMap } from '@/components/maps/WorldChoroplethMap'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { useI18n } from '@/i18n/I18nProvider'
import { formatNumber, formatPercent } from '@/lib/format'
import {
  useCountryUploadStats,
  useDashboardKpis,
  useDatasetSamples,
  useMonthlyUploads,
  useRecentUploadsProfile,
  useTrainingClassDistribution,
} from '@/hooks/useDashboardData'

const TOP_COUNTRIES_SHOWN = 3

export function DashboardPage() {
  const { t, locale } = useI18n()
  const [mapMode, setMapMode] = useState<'choropleth' | 'bubbles'>('choropleth')

  const kpisQuery = useDashboardKpis()
  const distributionQuery = useTrainingClassDistribution()
  const monthlyQuery = useMonthlyUploads()
  const profileQuery = useRecentUploadsProfile()
  const countryStatsQuery = useCountryUploadStats()
  const samplesQuery = useDatasetSamples()

  const kpis = kpisQuery.data
  const countryStats = countryStatsQuery.data

  const topCountriesLabel = countryStats
    ? `${t('dashboard.uploadsByCountry.top')}: ${[...countryStats]
        .sort((a, b) => b.uploads - a.uploads)
        .slice(0, TOP_COUNTRIES_SHOWN)
        .map((stat) => `${stat.countryName} ${formatNumber(stat.uploads, locale)}`)
        .join(' · ')}`
    : ''

  return (
    <div className="flex min-h-0 w-full flex-col gap-3 px-4 py-3 sm:px-6 lg:h-full lg:overflow-hidden">
      <div className="flex shrink-0 flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1">
          <h1 className="text-xl font-semibold">{t('dashboard.title')}</h1>
          <p className="truncate text-sm text-muted-foreground">{t('dashboard.subtitle')}</p>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <Badge variant="warning">{t('common.simulatedData')}</Badge>
          <Button asChild size="sm">
            <Link to="/analyze">
              {t('dashboard.analyzeCta')} <ArrowRight />
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid shrink-0 grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          layout="inline"
          isLoading={kpisQuery.isLoading}
          label={t('dashboard.kpi.trainingImages')}
          value={kpis ? formatNumber(kpis.trainingImages, locale) : ''}
          hint={kpis?.trainingImagesBreakdown}
        />
        <KpiCard
          layout="inline"
          isLoading={kpisQuery.isLoading}
          label={t('dashboard.kpi.modelAccuracy')}
          value={kpis ? formatPercent(kpis.modelAccuracy, locale) : ''}
          trend={
            kpis
              ? { direction: 'up', label: `${kpis.modelAccuracyDeltaPts} pts vs. v2.3` }
              : undefined
          }
        />
        <KpiCard
          layout="inline"
          isLoading={kpisQuery.isLoading}
          label={t('dashboard.kpi.userPredictions')}
          value={kpis ? formatNumber(kpis.userPredictions, locale) : ''}
          hint={
            kpis
              ? `${formatNumber(kpis.userPredictionsThisMonth, locale)} ${t('dashboard.kpi.thisMonth')}`
              : undefined
          }
        />
        <KpiCard
          layout="inline"
          isLoading={kpisQuery.isLoading}
          label={t('dashboard.kpi.activeCountries')}
          value={kpis ? formatNumber(kpis.activeCountries, locale) : ''}
          hint={kpis ? `${kpis.activeContinents} ${t('dashboard.kpi.continents')}` : undefined}
        />
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 lg:grid-cols-12">
        <div className="flex min-h-0 flex-col gap-3 lg:col-span-3">
          <ChartCard
            className="min-h-64 lg:flex-1"
            title={t('dashboard.trainingDistribution.title')}
            subtitle={t('dashboard.trainingDistribution.subtitle')}
            isLoading={distributionQuery.isLoading}
          >
            {distributionQuery.data && <DonutChart data={distributionQuery.data} />}
          </ChartCard>

          <ChartCard
            className="shrink-0"
            title={t('dashboard.datasetSamples.title')}
            action={<KaggleLink />}
            isLoading={samplesQuery.isLoading}
          >
            {samplesQuery.data && <DatasetSampleGallery samples={samplesQuery.data} />}
          </ChartCard>
        </div>

        <ChartCard
          className="min-h-80 lg:col-span-6 lg:h-full"
          contentClassName="flex items-center justify-center"
          title={t('dashboard.uploadsByCountry.title')}
          subtitle={t('dashboard.uploadsByCountry.subtitle', { count: countryStats?.length ?? 0 })}
          isLoading={countryStatsQuery.isLoading}
          action={
            <ToggleGroup
              type="single"
              value={mapMode}
              onValueChange={(value) => value && setMapMode(value as typeof mapMode)}
            >
              <ToggleGroupItem value="choropleth">
                {t('dashboard.uploadsByCountry.choropleth')}
              </ToggleGroupItem>
              <ToggleGroupItem value="bubbles">
                {t('dashboard.uploadsByCountry.bubbles')}
              </ToggleGroupItem>
            </ToggleGroup>
          }
          footer={
            countryStats && (
              <div className="flex flex-wrap items-center justify-between gap-2">
                <ChoroplethScale
                  minLabel={t('dashboard.uploadsByCountry.min')}
                  maxLabel={t('dashboard.uploadsByCountry.max')}
                />
                <span className="truncate text-[11px] text-muted-foreground">
                  {topCountriesLabel}
                </span>
              </div>
            )
          }
        >
          {countryStats && <WorldChoroplethMap data={countryStats} mode={mapMode} />}
        </ChartCard>

        <div className="flex min-h-0 flex-col gap-3 lg:col-span-3">
          <ChartCard
            className="min-h-52 lg:flex-1"
            title={t('dashboard.uploadsByMonth.title')}
            subtitle={t('dashboard.uploadsByMonth.subtitle')}
            isLoading={monthlyQuery.isLoading}
          >
            {monthlyQuery.data && <MonthlyBarChart data={monthlyQuery.data} />}
          </ChartCard>

          <ChartCard
            className="min-h-52 lg:flex-1"
            title={t('dashboard.recentProfile.title')}
            subtitle={t('dashboard.recentProfile.subtitle')}
            isLoading={profileQuery.isLoading}
          >
            {profileQuery.data && <ConfidenceRadarChart data={profileQuery.data} />}
          </ChartCard>
        </div>
      </div>
    </div>
  )
}
