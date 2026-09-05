export type TumorClass = 'glioma' | 'meningioma' | 'pituitary' | 'healthy'

export const TUMOR_CLASSES: TumorClass[] = ['glioma', 'meningioma', 'pituitary', 'healthy']

/**
 * Metadatos del modelo que está sirviendo, declarados por el propio artefacto.
 *
 * El preproceso NO se escribe a mano en la interfaz: lo declara el modelo
 * empaquetado y la API lo expone en `GET /api/v1/meta`. Ver patrón «Transform».
 */
export interface ActiveModelInfo {
  modelVersion: string
  preprocessLabel: string
  simulatedInference: boolean
}

/**
 * Métodos de explicabilidad que el artefacto puede declarar.
 *
 * Hoy solo hay uno: sensibilidad por oclusión. El modelo se sirve como ONNX y
 * `onnxruntime` no calcula gradientes, así que Grad-CAM no es implementable
 * sobre el artefacto real; la oclusión responde a la misma pregunta usando
 * únicamente pasadas hacia adelante.
 */
export type ExplanationMethod = 'occlusion'

/**
 * Justificación espacial de una predicción, producida por el propio modelo.
 *
 * Igual que el preproceso, el método NO se reimplementa en el cliente: la UI
 * solo transporta y pinta lo que el artefacto devuelve. Ver patrón
 * «Explainable Predictions».
 */
export interface PredictionExplanation {
  /** Identificador estable del método, tal y como lo declara el artefacto. */
  method: ExplanationMethod
  /** Etiqueta legible con los parámetros reales, p. ej. «Oclusión 32 px · paso 16 px». */
  methodLabel: string
  /**
   * Mapa de influencia normalizado a [0,1] como imagen (data URI).
   *
   * La intensidad viaja en el canal alfa, de modo que la imagen sirve
   * directamente de máscara CSS sobre la MRI, sin decodificar ni recolorear.
   */
  influenceMapDataUri: string
}

export interface ClassificationResult {
  predictedClass: TumorClass
  confidenceByClass: Record<TumorClass, number>
  description: string
  modelVersion: string
  preprocess: string
  countryCode: string
  /** Ausente cuando la petición no pidió explicación: cuesta N inferencias extra. */
  explanation: PredictionExplanation | null
}
