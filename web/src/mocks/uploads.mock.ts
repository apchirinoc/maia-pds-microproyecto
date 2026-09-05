import type { TumorClass } from '@/types/classification'
import type {
  GroundTruthDiagnosis,
  GroundTruthSource,
  UploadHistorySummary,
  UploadRecord,
  UploadStatus,
} from '@/types/upload'
import { COUNTRIES } from './countries.mock'

/**
 * Agregados del histórico que NO dependen de la verdad de campo.
 *
 * Los dos KPI de verdad de campo (cobertura y precisión real medida) no están
 * aquí a propósito: se calculan en `uploads.service.ts` a partir de los
 * registros, para que reflejen cada diagnóstico que se registre en la sesión.
 */
export const UPLOAD_HISTORY_BASE_SUMMARY: Omit<UploadHistorySummary, 'groundTruth'> = {
  totalUploads: 12847,
  pendingReview: 214,
  averageConfidence: 94.8,
  discarded: 37,
}

const TUMOR_CLASSES: TumorClass[] = ['glioma', 'meningioma', 'pituitary', 'healthy']
const STATUSES: UploadStatus[] = ['validated', 'validated', 'validated', 'pending']

/**
 * Especialistas que firman las confirmaciones. Los mismos identificadores que
 * la semilla SQL (`model/scripts/dml/02_seed_verdad_campo.sql`).
 */
const SPECIALISTS: string[] = [
  'dra.moreno@hospital.example',
  'dr.iyer@hospital.example',
  'dr.almeida@hospital.example',
  'dra.rivas@hospital.example',
  'dr.keller@hospital.example',
]

/** Fuentes de evidencia, con los literales del ENUM `ground_truth_source`. */
const GROUND_TRUTH_SOURCES: GroundTruthSource[] = [
  'histopathology',
  'radiology_report',
  'follow_up_imaging',
  'specialist_review',
]

/**
 * Proporción de cargas que llegan a tener diagnóstico confirmado. La cobertura
 * real nunca es del 100 %: confirmar cuesta tiempo de especialista, y ése es
 * justamente el problema que el cap. 7 de «Introducing MLOps» describe.
 */
const GROUND_TRUTH_COVERAGE_RATE = 0.45

/**
 * Probabilidad de que una confirmación DISCREPE de la predicción. Sin
 * discrepancias la precisión real medida saldría 100 % y el circuito no
 * demostraría nada.
 */
const GROUND_TRUTH_MISMATCH_RATE = 0.18

/**
 * Semilla propia del reparto de verdad de campo. Con este valor el histórico
 * de 120 cargas queda, de forma completamente determinista, en:
 *     · 56 cargas confirmadas de 120  → cobertura       = 46,67 %
 *     · 44 aciertos y 12 discrepancias → precisión real = 78,57 %
 *       (21,43 % de las confirmadas discrepan de la predicción)
 * La primera discrepancia cae en la segunda fila del histórico, así que la
 * señal visual se ve sin cambiar de página.
 */
const GROUND_TRUTH_SEED = 2

function seededRandom(seed: number): () => number {
  let value = seed
  return () => {
    value = (value * 9301 + 49297) % 233280
    return value / 233280
  }
}

function buildUploadHistory(count: number): UploadRecord[] {
  const random = seededRandom(42)
  const records: UploadRecord[] = []
  // Base en UTC explícito: sin la «Z» el dato generado dependería de la zona
  // horaria de quien ejecuta, y el backend produciría timestamps distintos.
  const baseDate = new Date('2026-08-23T08:41:00Z')

  for (let i = 0; i < count; i += 1) {
    const tumorClass = TUMOR_CLASSES[Math.floor(random() * TUMOR_CLASSES.length)]
    const country = COUNTRIES[Math.floor(random() * COUNTRIES.length)]
    const status = STATUSES[Math.floor(random() * STATUSES.length)]
    const confidence = Math.round((0.82 + random() * 0.17) * 1000) / 10
    const capturedAt = new Date(baseDate.getTime() - i * 3 * 60 * 60 * 1000)
    const prefix = tumorClass === 'glioma' ? 'gl' : tumorClass === 'meningioma' ? 'me' : tumorClass === 'pituitary' ? 'pi' : 'no'

    records.push({
      id: `upl_${(0x9f31c4 - i).toString(16)}`,
      fileName: `Te-${prefix}_${String(1000 + i).slice(-4)}.jpg`,
      capturedAt: capturedAt.toISOString(),
      countryName: country.name,
      prediction: tumorClass,
      confidence,
      status: i < 3 ? 'validated' : status,
      groundTruth: null,
    })
  }

  return records
}

/** Devuelve una clase distinta de la predicha, de forma determinista. */
function pickMismatchedClass(prediction: TumorClass, draw: number): TumorClass {
  const alternatives = TUMOR_CLASSES.filter((tumorClass) => tumorClass !== prediction)
  const position = Math.floor(draw * alternatives.length) % alternatives.length
  return alternatives[position]
}

/**
 * Reparte la verdad de campo sobre las cargas ya generadas.
 *
 * Usa su propia semilla para no alterar el resto del histórico, y sólo confirma
 * cargas no descartadas: una imagen descartada no se manda a un especialista.
 */
function assignGroundTruth(records: UploadRecord[]): UploadRecord[] {
  const random = seededRandom(GROUND_TRUTH_SEED)

  return records.map((record, index) => {
    if (record.status === 'discarded') return record
    if (random() > GROUND_TRUTH_COVERAGE_RATE) return record

    const isMismatch = random() < GROUND_TRUTH_MISMATCH_RATE
    const diagnosis = isMismatch
      ? pickMismatchedClass(record.prediction, random())
      : record.prediction

    // La confirmación siempre llega después de la carga: entre 2 y 9 días.
    const delayInDays = 2 + (index % 8)
    const confirmedAt = new Date(
      new Date(record.capturedAt).getTime() + delayInDays * 24 * 60 * 60 * 1000,
    )

    const groundTruth: GroundTruthDiagnosis = {
      diagnosis,
      confirmedBy: SPECIALISTS[index % SPECIALISTS.length],
      confirmedAt: confirmedAt.toISOString(),
      source: GROUND_TRUTH_SOURCES[index % GROUND_TRUTH_SOURCES.length],
    }

    return { ...record, groundTruth }
  })
}

/**
 * Histórico simulado. Es mutable a propósito: registrar un diagnóstico desde la
 * interfaz actualiza este mismo array, como haría un UPDATE contra la base de
 * datos, y los KPI se recalculan solos en la siguiente consulta.
 */
export const UPLOAD_HISTORY: UploadRecord[] = assignGroundTruth(buildUploadHistory(120))
