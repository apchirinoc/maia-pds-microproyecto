import { useMemo, useState } from 'react'
import { PageContainer } from '@/components/layout/PageContainer'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { ImageDropzone, type SelectedImage } from '@/components/features/analyze/ImageDropzone'
import { ClassSamplePicker } from '@/components/features/analyze/ClassSamplePicker'
import { ClassificationResultPanel, type ClassificationStatus } from '@/components/features/analyze/ClassificationResultPanel'
import { CountryPickerMap } from '@/components/maps/CountryPickerMap'
import { useI18n } from '@/i18n/I18nProvider'
import { useActiveModelInfo, useClassifyImage } from '@/hooks/useClassifyImage'
import { useDatasetSamples } from '@/hooks/useDashboardData'
import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { COUNTRIES } from '@/mocks/countries.mock'
import type { DatasetSample } from '@/mocks/dashboard.mock'

export function AnalyzeImagePage() {
  const { t } = useI18n()
  const samplesQuery = useDatasetSamples()
  const modelInfoQuery = useActiveModelInfo()
  const classifyMutation = useClassifyImage()

  const [selectedImage, setSelectedImage] = useState<SelectedImage | null>(null)
  const [selectedCountryCode, setSelectedCountryCode] = useState<string | null>(null)

  const selectedCountry = useMemo(
    () => COUNTRIES.find((country) => country.code === selectedCountryCode) ?? null,
    [selectedCountryCode],
  )

  function handleFileSelected(file: File) {
    setSelectedImage({ kind: 'upload', file, previewUrl: URL.createObjectURL(file) })
    classifyMutation.reset()
  }

  function handleSampleSelected(sample: DatasetSample) {
    setSelectedImage({ kind: 'sample', tumorClass: sample.tumorClass, fileName: sample.fileName })
    classifyMutation.reset()
  }

  function handleClearImage() {
    setSelectedImage(null)
    classifyMutation.reset()
  }

  function handleSelectCountry(code: string | null) {
    setSelectedCountryCode(code)
    classifyMutation.reset()
  }

  function handleClassify() {
    if (!selectedCountryCode) return
    classifyMutation.mutate({
      countryCode: selectedCountryCode,
      hint: selectedImage?.kind === 'sample' ? selectedImage.tumorClass : undefined,
      // El mapa de influencia se pide de forma explícita: en la API real
      // cuesta una inferencia por cada parche ocluido.
      explain: true,
    })
  }

  function handleDownloadReport() {
    const result = classifyMutation.data
    if (!result) return
    const lines = [
      `BrainNeuroScan · ${t('common.simulatedInference')}`,
      `${t('analyze.step3.model')}: ${result.modelVersion}`,
      `${t('analyze.step3.preprocess')}: ${result.preprocess}`,
      `${t('analyze.step3.origin')}: ${selectedCountry?.name ?? ''}`,
      ...(result.explanation
        ? [`${t('analyze.step3.explanationMethod')}: ${result.explanation.methodLabel}`]
        : []),
      '',
      `${t(`classes.${result.predictedClass}`)}: ${result.confidenceByClass[result.predictedClass].toFixed(1)}%`,
      ...Object.entries(result.confidenceByClass)
        .filter(([tumorClass]) => tumorClass !== result.predictedClass)
        .map(([tumorClass, value]) => `${t(`classes.${tumorClass}`)}: ${value.toFixed(1)}%`),
    ]
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `brainneuroscan-report-${Date.now()}.txt`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  const status: ClassificationStatus = classifyMutation.isPending
    ? 'loading'
    : classifyMutation.data
      ? 'result'
      : selectedImage && selectedCountryCode
        ? 'ready'
        : 'empty'


  return (
    <PageContainer className="flex flex-col gap-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{t('analyze.title')}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t('analyze.subtitle')}</p>
        </div>
        {modelInfoQuery.data?.simulatedInference && (
          <Badge variant="info">{t('common.simulatedInference')}</Badge>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>{t('analyze.step1.label')}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <ImageDropzone
              selectedImage={selectedImage}
              onFileSelected={handleFileSelected}
              onClear={handleClearImage}
            />
            {samplesQuery.data && (
              <ClassSamplePicker
                samples={samplesQuery.data}
                selectedTumorClass={selectedImage?.kind === 'sample' ? selectedImage.tumorClass : null}
                onSelectSample={handleSampleSelected}
              />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('analyze.step2.label')}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="relative">
              <Select
                value={selectedCountryCode ?? ''}
                onValueChange={(value) => handleSelectCountry(value === '__CLEAR__' ? null : value)}
              >
                <SelectTrigger className={cn(selectedCountryCode && 'pr-8')}>
                  <SelectValue placeholder={t('analyze.step2.selectCountry')} />
                </SelectTrigger>
                <SelectContent>
                  {selectedCountryCode && (
                    <>
                      <SelectItem value="__CLEAR__" className="text-muted-foreground font-medium">
                        ✕ {t('analyze.step2.clearSelection')}
                      </SelectItem>
                      <Separator className="my-1" />
                    </>
                  )}
                  {COUNTRIES.map((country) => (
                    <SelectItem key={country.code} value={country.code}>
                      {country.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedCountryCode && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    handleSelectCountry(null)
                  }}
                  title={t('analyze.step2.clearSelection')}
                  aria-label={t('analyze.step2.clearSelection')}
                  className="absolute right-8 top-1/2 -translate-y-1/2 rounded-full p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                >
                  <X className="size-3.5" />
                </button>
              )}
            </div>

            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Separator className="flex-1" />
              {t('analyze.step2.orMap')}
              <Separator className="flex-1" />
            </div>

            <CountryPickerMap
              selectedCountryCode={selectedCountryCode}
              onSelectCountry={handleSelectCountry}
            />

            {selectedCountry ? (
              <div className="flex items-center justify-between gap-2">
                <Badge variant="info" className="flex items-center gap-1.5 py-1 px-2.5 text-xs">
                  <span>📍 {selectedCountry.name}</span>
                  <button
                    type="button"
                    onClick={() => handleSelectCountry(null)}
                    title={t('analyze.step2.clearSelection')}
                    aria-label={t('analyze.step2.clearSelection')}
                    className="ml-0.5 rounded-full p-0.5 transition-colors hover:bg-black/10 dark:hover:bg-white/20"
                  >
                    <X className="size-3" />
                  </button>
                </Badge>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => handleSelectCountry(null)}
                  className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
                >
                  {t('analyze.step2.clearSelection')}
                </Button>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">{t('dashboard.uploadsByCountry.noSelection')}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('analyze.step3.label')}</CardTitle>
          </CardHeader>
          <CardContent className="min-h-72">
            <ClassificationResultPanel
              status={status}
              countryName={selectedCountry?.name ?? null}
              modelInfo={modelInfoQuery.data ?? null}
              result={classifyMutation.data ?? null}
              selectedImage={selectedImage}
              onClassify={handleClassify}
              onNewImage={handleClearImage}
              onDownloadReport={handleDownloadReport}
            />
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  )
}
