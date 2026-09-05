import type {
  ActiveModelInfo,
  ClassificationResult,
  PredictionExplanation,
  TumorClass,
} from '@/types/classification'
import { TUMOR_CLASSES } from '@/types/classification'

const CLASS_DESCRIPTIONS: Record<TumorClass, string> = {
  glioma: 'Masa intraaxial con realce heterogéneo · corte sagital',
  meningioma: 'Lesión extraaxial de base dural bien delimitada',
  pituitary: 'Lesión selar con posible extensión supraselar',
  healthy: 'Sin hallazgos compatibles con tumor · parénquima normal',
}

/**
 * Refleja lo que el artefacto de MLflow declara en sus metadatos
 * (`preprocess_label`, derivado de `PreprocessConfig.label`). Cuando exista
 * backend, esto lo devuelve `GET /api/v1/meta`.
 */
export const ACTIVE_MODEL_INFO: ActiveModelInfo = {
  modelVersion: 'EffNetB3-BT · v2.4',
  preprocessLabel: '224×224 · CLAHE',
  simulatedInference: true,
}

/**
 * Etiqueta que declara el artefacto real (`OcclusionConfig.label` en
 * `ml_project/pipelines/explainability.py`). No se compone en la interfaz:
 * aquí se replica solo porque la inferencia está simulada.
 */
const EXPLANATION_METHOD_LABEL = 'Oclusión 32 px · paso 16 px'

/** Celdas por lado de la rejilla de oclusión simulada. */
const INFLUENCE_GRID_SIZE = 14

/**
 * Geometría de la lesión, espejo de `MriThumbnail` (viewBox `0 0 100 100`).
 *
 * El mapa simulado tiene que caer sobre la lesión que el usuario ve dibujada;
 * si divergieran, la explicación parecería señalar cualquier cosa.
 */
const LESION_FOCUS: Record<TumorClass, { cx: number; cy: number; r: number } | null> = {
  glioma: { cx: 65, cy: 60, r: 12 },
  meningioma: { cx: 40, cy: 35, r: 12 },
  pituitary: { cx: 49, cy: 48, r: 8 },
  healthy: null,
}

/** Cráneo dibujado por `MriThumbnail`: fuera de él, ocluir no cambia nada. */
const SKULL = { cx: 50, cy: 50, rx: 42, ry: 46 }

/** Centro del parénquima, foco difuso cuando no hay lesión. */
const PARENCHYMA = { cx: 50, cy: 52 }

function createSeed(...parts: string[]): number {
  // FNV-1a de 32 bits: determinista y suficiente para sembrar el generador.
  let hash = 0x811c9dc5
  const source = parts.join('|')
  for (let index = 0; index < source.length; index += 1) {
    hash ^= source.charCodeAt(index)
    hash = Math.imul(hash, 0x01000193)
  }
  return hash >>> 0
}

/** Generador `mulberry32`: misma semilla, misma secuencia, sin dependencias. */
function createRandom(seed: number): () => number {
  let state = seed >>> 0
  return () => {
    state = (state + 0x6d2b79f5) >>> 0
    let value = Math.imul(state ^ (state >>> 15), 1 | state)
    value = (value + Math.imul(value ^ (value >>> 7), 61 | value)) ^ value
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296
  }
}

function gaussian(distance: number, sigma: number): number {
  return Math.exp(-(distance * distance) / (2 * sigma * sigma))
}

function isInsideSkull(x: number, y: number): boolean {
  const dx = (x - SKULL.cx) / SKULL.rx
  const dy = (y - SKULL.cy) / SKULL.ry
  return dx * dx + dy * dy <= 1
}

/**
 * Construye la rejilla de influencia normalizada a [0,1].
 *
 * Imita lo que produce la sensibilidad por oclusión sobre una MRI real: un
 * núcleo dominante sobre la lesión, un lóbulo secundario más débil, una
 * textura tenue en el resto del parénquima y cero fuera del cráneo, porque
 * tapar el fondo negro no mueve la predicción.
 */
function buildInfluenceCells(predictedClass: TumorClass, seed: number): number[] {
  const random = createRandom(seed)
  const focus = LESION_FOCUS[predictedClass]
  const step = 100 / INFLUENCE_GRID_SIZE

  // Lóbulo secundario determinista: la oclusión casi nunca señala un único punto.
  const echoAngle = random() * Math.PI * 2
  const echoDistance = 14 + random() * 8
  const echoCenter = focus
    ? {
        cx: focus.cx + Math.cos(echoAngle) * echoDistance,
        cy: focus.cy + Math.sin(echoAngle) * echoDistance,
      }
    : PARENCHYMA

  const cells: number[] = []
  for (let row = 0; row < INFLUENCE_GRID_SIZE; row += 1) {
    for (let column = 0; column < INFLUENCE_GRID_SIZE; column += 1) {
      const x = (column + 0.5) * step
      const y = (row + 0.5) * step

      if (!isInsideSkull(x, y)) {
        cells.push(0)
        continue
      }

      let intensity = 0.05 + random() * 0.12
      if (focus) {
        const toFocus = Math.hypot(x - focus.cx, y - focus.cy)
        const toEcho = Math.hypot(x - echoCenter.cx, y - echoCenter.cy)
        intensity += gaussian(toFocus, focus.r * 1.15)
        intensity += 0.32 * gaussian(toEcho, focus.r * 1.6)
      } else {
        // Sin lesión, la evidencia de «sano» está repartida por el parénquima.
        const toCenter = Math.hypot(x - PARENCHYMA.cx, y - PARENCHYMA.cy)
        intensity += 0.55 * gaussian(toCenter, 26)
      }
      cells.push(intensity)
    }
  }

  const peak = Math.max(...cells)
  return peak > 0 ? cells.map((value) => Math.round((value / peak) * 1000) / 1000) : cells
}

/**
 * Serializa la rejilla como imagen SVG en un data URI.
 *
 * La influencia va en la opacidad (canal alfa), igual que en el PNG que
 * devuelve el artefacto real, para que el componente de superposición
 * funcione sin cambios cuando se sustituyan los datos simulados por la API.
 */
function buildInfluenceMapDataUri(cells: number[]): string {
  const step = 100 / INFLUENCE_GRID_SIZE
  const rects = cells
    .map((intensity, index) => {
      if (intensity < 0.04) return ''
      const column = index % INFLUENCE_GRID_SIZE
      const row = Math.floor(index / INFLUENCE_GRID_SIZE)
      const x = Math.round(column * step * 100) / 100
      const y = Math.round(row * step * 100) / 100
      const side = Math.round(step * 1.04 * 100) / 100
      return `<rect x="${x}" y="${y}" width="${side}" height="${side}" fill="#fff" fill-opacity="${intensity}"/>`
    })
    .join('')

  const svg =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="224" height="224">' +
    '<defs><filter id="soften" x="-25%" y="-25%" width="150%" height="150%">' +
    '<feGaussianBlur stdDeviation="2.4"/></filter></defs>' +
    `<g filter="url(#soften)">${rects}</g></svg>`

  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
}

/**
 * Explicación simulada, determinista para un mismo par clase/país.
 *
 * Repetir la clasificación de la misma muestra devuelve el mismo mapa, tal y
 * como garantiza `compute_occlusion_map` en el artefacto.
 */
export function generateExplanation(
  predictedClass: TumorClass,
  countryCode: string,
): PredictionExplanation {
  const cells = buildInfluenceCells(predictedClass, createSeed(predictedClass, countryCode))
  return {
    method: 'occlusion',
    methodLabel: EXPLANATION_METHOD_LABEL,
    influenceMapDataUri: buildInfluenceMapDataUri(cells),
  }
}

function distributeConfidence(predicted: TumorClass): Record<TumorClass, number> {
  const primary = 90 + Math.random() * 8
  const remaining = 100 - primary
  const others = TUMOR_CLASSES.filter((tumorClass) => tumorClass !== predicted)
  const weights = others.map(() => Math.random())
  const weightSum = weights.reduce((sum, weight) => sum + weight, 0)

  const confidenceByClass = { [predicted]: Math.round(primary * 10) / 10 } as Record<TumorClass, number>
  others.forEach((tumorClass, index) => {
    confidenceByClass[tumorClass] = Math.round((remaining * (weights[index] / weightSum)) * 10) / 10
  })

  return confidenceByClass
}

export function generateClassificationResult(
  countryCode: string,
  hint?: TumorClass,
  explain = true,
): ClassificationResult {
  const predictedClass = hint ?? TUMOR_CLASSES[Math.floor(Math.random() * TUMOR_CLASSES.length)]

  return {
    predictedClass,
    confidenceByClass: distributeConfidence(predictedClass),
    description: CLASS_DESCRIPTIONS[predictedClass],
    modelVersion: ACTIVE_MODEL_INFO.modelVersion,
    preprocess: ACTIVE_MODEL_INFO.preprocessLabel,
    countryCode,
    explanation: explain ? generateExplanation(predictedClass, countryCode) : null,
  }
}
