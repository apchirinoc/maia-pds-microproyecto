import type { TumorClass } from './classification'

export type ModelStatus = 'production' | 'archived' | 'validation' | 'baseline'

export interface DeployedModel {
  id: string
  name: string
  version: string
  architecture: string
  accuracy: number
  f1: number
  sizeMb: number
  status: ModelStatus
  weightsFileName: string
}

export interface ModelMetrics {
  accuracy: number
  precisionMacro: number
  recallMacro: number
  auc: number
}

export type ConfusionMatrix = Record<TumorClass, Record<TumorClass, number>>

export interface DeploymentEvent {
  id: string
  label: string
  date: string
  author: string
}

export interface ModelDetail extends DeployedModel {
  trainingImages: number
  testImages: number
  activeSince: string
  metrics: ModelMetrics
  confusionMatrix: ConfusionMatrix
  classPerformance: Record<TumorClass, number>
  deploymentHistory: DeploymentEvent[]
  targetDraftVersion: string
  previousVersion?: string
}

export interface ModelRegistrySummary {
  productionModel: Pick<DeployedModel, 'name' | 'version'>
  activeSince: string
  accuracyTest: number
  meanLatencyMs: number
  storageGb: number
  archivedVersions: number
}

/**
 * Una versión disponible en el Model Registry de MLflow (respaldado por S3).
 * Es lo que se selecciona para poner en producción, en lugar de subir un archivo.
 */
export interface RegistryModelVersion {
  version: string
  alias: string | null
  arch: string
  accuracy: number
  f1: number
  recall: number
  createdAt: string
  runId: string
  artifactUri: string
}
