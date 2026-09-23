import type { ActiveModelInfo, ClassificationResult, TumorClass } from '@/types/classification'
import { ACTIVE_MODEL_INFO, generateClassificationResult } from '@/mocks/classification.mock'
import { apiFetch } from '@/lib/api/client'
import { conOrigenDeDatos } from '@/lib/api/gateway'
import { randomDelay } from './delay'

export interface ClassifyImageParams {
  countryCode: string
  hint?: TumorClass
  /**
   * Pide también el mapa de influencia.
   *
   * En la API se traduce en `params={"explain": true}` sobre el artefacto, que
   * cuesta una inferencia por parche ocluido. Por eso es una decisión explícita
   * de quien llama y no un efecto secundario de clasificar.
   */
  explain?: boolean
  /** Imagen subida por el usuario. */
  file?: File
  /**
   * URL de la muestra del dataset que se está mostrando. Se descarga y se envía
   * como archivo: la inferencia real necesita los bytes de la imagen.
   */
  sampleImageUrl?: string
}

async function cargarMuestra(url: string): Promise<File> {
  const respuesta = await fetch(url)
  const contenido = await respuesta.blob()
  // Un recurso inexistente devuelve el index.html del SPA con estado 200.
  if (!respuesta.ok || !contenido.type.startsWith('image/')) {
    throw new Error(`No se pudo cargar la imagen de muestra ${url}`)
  }
  const nombre = url.split('/').pop() || 'muestra.jpg'
  return new File([contenido], nombre, { type: contenido.type })
}

export async function classifyImage({
  countryCode,
  hint,
  explain = true,
  file,
  sampleImageUrl,
}: ClassifyImageParams): Promise<ClassificationResult> {
  return conOrigenDeDatos(
    async () => {
      const formulario = new FormData()
      formulario.append('countryCode', countryCode)
      formulario.append('explain', String(explain))
      if (hint !== undefined) formulario.append('hint', hint)
      const imagen = file ?? (sampleImageUrl ? await cargarMuestra(sampleImageUrl) : undefined)
      if (imagen !== undefined) formulario.append('file', imagen)
      return apiFetch<ClassificationResult>('/api/v1/classifications', {
        method: 'POST',
        body: formulario,
      })
    },
    async () => {
      await randomDelay(900, 1600)
      return generateClassificationResult(countryCode, hint, explain)
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
