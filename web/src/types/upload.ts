import type { TumorClass } from './classification'

export type UploadStatus = 'validated' | 'pending' | 'discarded'

/**
 * Fuente de la que procede un diagnóstico confirmado.
 *
 * Espeja literal por literal el ENUM `ground_truth_source` de
 * `model/scripts/ddl/01_tipos_verdad_campo.sql`, de menor a mayor nivel
 * de evidencia: lectura de especialista, informe radiológico o imagen de
 * seguimiento, y anatomía patológica como patrón oro.
 */
export type GroundTruthSource =
  | 'specialist_review'
  | 'radiology_report'
  | 'follow_up_imaging'
  | 'histopathology'

/**
 * Verdad de campo (ground truth) de una carga: el diagnóstico realmente
 * confirmado por un especialista, no la predicción del modelo.
 *
 * Corresponde a la fila vigente de `ground_truth_diagnoses` para esa carga.
 */
export interface GroundTruthDiagnosis {
  diagnosis: TumorClass
  /** Quién confirmó el diagnóstico (login o correo profesional). */
  confirmedBy: string
  /** Cuándo se confirmó, en ISO-8601 UTC. */
  confirmedAt: string
  source: GroundTruthSource
}

export interface UploadRecord {
  id: string
  fileName: string
  capturedAt: string
  countryName: string
  /** Clase predicha por el modelo. Es un proxy, no el diagnóstico real. */
  prediction: TumorClass
  confidence: number
  status: UploadStatus
  /** Diagnóstico confirmado; `null` mientras nadie lo haya registrado. */
  groundTruth: GroundTruthDiagnosis | null
}

/**
 * Métricas del circuito de verdad de campo, calculadas siempre a partir de los
 * registros y nunca declaradas como constantes.
 *
 * Equivalen a la vista `vw_ground_truth_performance` del modelo de datos.
 */
export interface GroundTruthMetrics {
  /** Cargas consideradas (denominador de la cobertura). */
  totalUploads: number
  /** Cargas con diagnóstico confirmado. */
  confirmedUploads: number
  /** Confirmadas en las que el modelo acertó. */
  correctPredictions: number
  /** Confirmadas en las que el diagnóstico discrepa de la predicción. */
  mismatchedPredictions: number
  /** Cobertura de verdad de campo, en porcentaje (0-100). */
  coverage: number
  /** Precisión real medida en porcentaje; `null` si aún no hay confirmadas. */
  measuredAccuracy: number | null
}

export interface UploadHistorySummary {
  totalUploads: number
  pendingReview: number
  averageConfidence: number
  discarded: number
  groundTruth: GroundTruthMetrics
}

/** Datos que envía la interfaz para registrar un diagnóstico confirmado. */
export interface RecordGroundTruthInput {
  uploadId: string
  diagnosis: TumorClass
  confirmedBy: string
  source: GroundTruthSource
}

export interface UploadHistoryFilters {
  tumorClass: TumorClass | 'all'
  page: number
  pageSize: number
}

export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}
