import type {
  GroundTruthMetrics,
  PaginatedResult,
  RecordGroundTruthInput,
  UploadHistoryFilters,
  UploadHistorySummary,
  UploadRecord,
} from '@/types/upload'
import { UPLOAD_HISTORY, UPLOAD_HISTORY_BASE_SUMMARY } from '@/mocks/uploads.mock'
import { apiFetch, apiFetchBlob } from '@/lib/api/client'
import { conOrigenDeDatos } from '@/lib/api/gateway'
import { randomDelay } from './delay'

/**
 * Calcula los dos KPI del circuito de verdad de campo a partir de los
 * registros. Réplica exacta de la vista `vw_ground_truth_performance`
 * (`model/scripts/ddl/04_vistas_verdad_campo.sql`) y de
 * `calcular_metricas_verdad_campo` en el API:
 *
 *     cobertura        = confirmadas / total
 *     precisión medida = aciertos    / confirmadas
 *
 * Las cargas sin confirmar NO cuentan como fallo: quedan fuera del numerador y
 * del denominador de la precisión. «Desconocido» no es «error»; confundirlos
 * es lo que hace inservible una métrica de rendimiento real.
 */
export function computeGroundTruthMetrics(records: UploadRecord[]): GroundTruthMetrics {
  const totalUploads = records.length
  const confirmed = records.filter((record) => record.groundTruth !== null)
  const correctPredictions = confirmed.filter(
    (record) => record.groundTruth?.diagnosis === record.prediction,
  ).length

  return {
    totalUploads,
    confirmedUploads: confirmed.length,
    correctPredictions,
    mismatchedPredictions: confirmed.length - correctPredictions,
    coverage: totalUploads === 0 ? 0 : (confirmed.length / totalUploads) * 100,
    measuredAccuracy:
      confirmed.length === 0 ? null : (correctPredictions / confirmed.length) * 100,
  }
}

export async function getUploadHistorySummary(): Promise<UploadHistorySummary> {
  return conOrigenDeDatos(
    () => apiFetch<UploadHistorySummary>('/api/v1/uploads/summary', { autenticada: true }),
    async () => {
      await randomDelay(250, 450)
      return {
        ...UPLOAD_HISTORY_BASE_SUMMARY,
        groundTruth: computeGroundTruthMetrics(UPLOAD_HISTORY),
      }
    },
  )
}

export async function getUploadHistory(
  filters: UploadHistoryFilters,
): Promise<PaginatedResult<UploadRecord>> {
  const consulta = new URLSearchParams({
    tumorClass: filters.tumorClass,
    page: String(filters.page),
    pageSize: String(filters.pageSize),
  })

  return conOrigenDeDatos(
    () =>
      apiFetch<PaginatedResult<UploadRecord>>(`/api/v1/uploads?${consulta}`, {
        autenticada: true,
      }),
    async () => {
      await randomDelay(300, 550)
      const filtered =
        filters.tumorClass === 'all'
          ? UPLOAD_HISTORY
          : UPLOAD_HISTORY.filter((record) => record.prediction === filters.tumorClass)

      const start = (filters.page - 1) * filters.pageSize
      return {
        items: filtered.slice(start, start + filters.pageSize),
        total: filtered.length,
        page: filters.page,
        pageSize: filters.pageSize,
      }
    },
  )
}

/**
 * Registra el diagnóstico confirmado de una carga.
 *
 * Sustituye la confirmación vigente, igual que impone el índice único parcial
 * de `ground_truth_diagnoses`.
 */
export async function recordGroundTruth(input: RecordGroundTruthInput): Promise<UploadRecord> {
  return conOrigenDeDatos(
    () =>
      apiFetch<UploadRecord>(
        `/api/v1/uploads/${encodeURIComponent(input.uploadId)}/ground-truth`,
        {
          method: 'POST',
          json: {
            diagnosis: input.diagnosis,
            confirmedBy: input.confirmedBy,
            source: input.source,
          },
          autenticada: true,
        },
      ),
    async () => {
      await randomDelay(400, 700)
      const record = UPLOAD_HISTORY.find((item) => item.id === input.uploadId)
      if (!record) {
        throw new Error(`UPLOAD_NOT_FOUND:${input.uploadId}`)
      }
      record.groundTruth = {
        diagnosis: input.diagnosis,
        confirmedBy: input.confirmedBy,
        confirmedAt: new Date().toISOString(),
        source: input.source,
      }
      return record
    },
  )
}

export async function exportUploadHistoryCsv(): Promise<Blob> {
  return conOrigenDeDatos(
    () => apiFetchBlob('/api/v1/uploads/export', { autenticada: true }),
    async () => {
      await randomDelay(400, 700)
      const header =
        'id,fileName,capturedAt,countryName,prediction,confidence,status,groundTruth,groundTruthSource,confirmedBy,confirmedAt,isCorrect\n'
      const rows = UPLOAD_HISTORY.map((record) =>
        [
          record.id,
          record.fileName,
          record.capturedAt,
          record.countryName,
          record.prediction,
          record.confidence,
          record.status,
          record.groundTruth?.diagnosis ?? '',
          record.groundTruth?.source ?? '',
          record.groundTruth?.confirmedBy ?? '',
          record.groundTruth?.confirmedAt ?? '',
          // Vacío, no «false», cuando la carga aún no tiene diagnóstico confirmado.
          record.groundTruth ? String(record.groundTruth.diagnosis === record.prediction) : '',
        ].join(','),
      ).join('\n')
      return new Blob([header + rows], { type: 'text/csv;charset=utf-8;' })
    },
  )
}

export async function addUploadsToDataset(ids: string[]): Promise<void> {
  return conOrigenDeDatos(
    async () => {
      await apiFetch<{ accepted: number }>('/api/v1/uploads/add-to-dataset', {
        method: 'POST',
        json: ids,
        autenticada: true,
      })
    },
    async () => {
      await randomDelay(500, 900)
    },
  )
}
