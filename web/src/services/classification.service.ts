import type { ActiveModelInfo, ClassificationResult } from '@/types/classification'
import { ACTIVE_MODEL_INFO, generateClassificationResult } from '@/mocks/classification.mock'
import { apiFetch } from '@/lib/api/client'
import { conOrigenDeDatos } from '@/lib/api/gateway'
import { randomDelay } from './delay'

export interface ClassifyImageParams {
  countryCode: string
  requestId: number
  /**
   * Pide también el mapa de influencia.
   *
   * En la API se traduce en `params={"explain": true}` sobre el artefacto, que
   * cuesta una inferencia por parche ocluido. Por eso es una decisión explícita
   * de quien llama y no un efecto secundario de clasificar.
   */
  explain?: boolean
  /** Bytes de la misma imagen visible, tanto en cargas como en muestras. */
  file: File
}

export async function classifyImage({
  countryCode,
  explain = false,
  file,
}: ClassifyImageParams): Promise<ClassificationResult> {
  return conOrigenDeDatos(
    () => {
      const formulario = new FormData()
      formulario.append('countryCode', countryCode)
      formulario.append('explain', String(explain))
      formulario.append('file', file)
      return apiFetch<ClassificationResult>('/api/v1/classifications', {
        method: 'POST',
        body: formulario,
        timeoutMs: 120000,
      })
    },
    async () => {
      await randomDelay(900, 1600)
      return generateClassificationResult(countryCode, undefined, explain)
    },
  )
}

export async function getActiveModelInfo(): Promise<ActiveModelInfo> {
  return conOrigenDeDatos(
    () => apiFetch<ActiveModelInfo>('/api/v1/classifications/model-info'),
    async () => {
      await randomDelay(150, 300)
      return ACTIVE_MODEL_INFO
    },
  )
}
