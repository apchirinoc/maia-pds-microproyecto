import type { ConfusionMatrix, DeployedModel, ModelDetail, ModelRegistrySummary } from '@/types/model'

export const MODEL_REGISTRY_SUMMARY: ModelRegistrySummary = {
  productionModel: { name: 'EffNetB3-BT', version: 'v2.4' },
  activeSince: '2026-08-12',
  accuracyTest: 98.4,
  meanLatencyMs: 184,
  storageGb: 6.2,
  archivedVersions: 2,
}

export const DEPLOYED_MODELS: DeployedModel[] = [
  {
    id: 'effnetb3-bt-v2.4',
    name: 'EffNetB3-BT',
    version: 'v2.4',
    architecture: 'EfficientNet-B3',
    accuracy: 98.4,
    f1: 0.981,
    sizeMb: 47,
    status: 'production',
    weightsFileName: 'effnetb3_bt_v2.4.onnx',
  },
  {
    id: 'effnetb3-bt-v2.3',
    name: 'EffNetB3-BT',
    version: 'v2.3',
    architecture: 'EfficientNet-B3',
    accuracy: 97.2,
    f1: 0.968,
    sizeMb: 47.3,
    status: 'archived',
    weightsFileName: 'effnetb3_bt_v2.3.onnx',
  },
  {
    id: 'resnet50-bt-v1.8',
    name: 'ResNet50-BT',
    version: 'v1.8',
    architecture: 'ResNet-50',
    accuracy: 95.6,
    f1: 0.951,
    sizeMb: 98.4,
    status: 'archived',
    weightsFileName: 'resnet50_bt_v1.8.h5',
  },
  {
    id: 'vit-b16-bt-v0.9',
    name: 'ViT-B16-BT',
    version: 'v0.9',
    architecture: 'ViT-B/16',
    accuracy: 96.9,
    f1: 0.964,
    sizeMb: 331,
    status: 'validation',
    weightsFileName: 'vit_b16_v0.9.pt',
  },
  {
    id: 'cnn-base-v1.0',
    name: 'CNN-Base',
    version: 'v1.0',
    architecture: 'CNN · 6 capas',
    accuracy: 91.3,
    f1: 0.902,
    sizeMb: 12.8,
    status: 'baseline',
    weightsFileName: 'cnn_base_v1.0.h5',
  },
]

function buildConfusionMatrix(diagonalStrength: number): ConfusionMatrix {
  const off = Math.round((1 - diagonalStrength) * 12)
  return {
    glioma: { glioma: 295, meningioma: 4, pituitary: 1, healthy: off },
    meningioma: { glioma: 6, meningioma: 297, pituitary: 3, healthy: off },
    pituitary: { glioma: 1, meningioma: 2, pituitary: 297, healthy: off },
    healthy: { glioma: 0, meningioma: 1, pituitary: 0, healthy: 404 },
  }
}

const DEFAULT_DEPLOYMENT_HISTORY = [
  { id: 'evt-1', label: 'deployedToProduction', date: '2026-04-12', author: 'm.rivera' },
  { id: 'evt-2', label: 'validated', date: '2026-04-10', author: 'a.suarez' },
  { id: 'evt-3', label: 'trainingCompleted', date: '2026-04-06', author: 'pipeline-ci' },
]

export const MODEL_DETAILS: Record<string, ModelDetail> = {
  'effnetb3-bt-v2.4': {
    ...DEPLOYED_MODELS[0],
    trainingImages: 5712,
    testImages: 1311,
    activeSince: '2026-08-12',
    metrics: { accuracy: 98.4, precisionMacro: 0.983, recallMacro: 0.979, auc: 0.997 },
    confusionMatrix: buildConfusionMatrix(0.98),
    classPerformance: { glioma: 0.983, meningioma: 0.97, pituitary: 0.99, healthy: 0.997 },
    deploymentHistory: DEFAULT_DEPLOYMENT_HISTORY,
    targetDraftVersion: 'v2.5',
    previousVersion: 'v2.3',
  },
  'effnetb3-bt-v2.3': {
    ...DEPLOYED_MODELS[1],
    trainingImages: 5400,
    testImages: 1280,
    activeSince: '2026-02-02',
    metrics: { accuracy: 97.2, precisionMacro: 0.969, recallMacro: 0.966, auc: 0.992 },
    confusionMatrix: buildConfusionMatrix(0.95),
    classPerformance: { glioma: 0.965, meningioma: 0.958, pituitary: 0.972, healthy: 0.988 },
    deploymentHistory: [
      { id: 'evt-1', label: 'archived', date: '2026-08-12', author: 'm.rivera' },
      { id: 'evt-2', label: 'deployedToProduction', date: '2026-02-02', author: 'm.rivera' },
    ],
    targetDraftVersion: 'v2.4',
  },
  'resnet50-bt-v1.8': {
    ...DEPLOYED_MODELS[2],
    trainingImages: 5100,
    testImages: 1200,
    activeSince: '2025-10-18',
    metrics: { accuracy: 95.6, precisionMacro: 0.949, recallMacro: 0.944, auc: 0.981 },
    confusionMatrix: buildConfusionMatrix(0.9),
    classPerformance: { glioma: 0.941, meningioma: 0.932, pituitary: 0.951, healthy: 0.97 },
    deploymentHistory: [
      { id: 'evt-1', label: 'archived', date: '2026-02-02', author: 'a.suarez' },
      { id: 'evt-2', label: 'deployedToProduction', date: '2025-10-18', author: 'a.suarez' },
    ],
    targetDraftVersion: 'v1.9',
  },
  'vit-b16-bt-v0.9': {
    ...DEPLOYED_MODELS[3],
    trainingImages: 5712,
    testImages: 1311,
    activeSince: '',
    metrics: { accuracy: 96.9, precisionMacro: 0.962, recallMacro: 0.958, auc: 0.989 },
    confusionMatrix: buildConfusionMatrix(0.93),
    classPerformance: { glioma: 0.955, meningioma: 0.948, pituitary: 0.964, healthy: 0.981 },
    deploymentHistory: [
      { id: 'evt-1', label: 'validated', date: '2026-08-28', author: 'a.suarez' },
      { id: 'evt-2', label: 'trainingCompleted', date: '2026-08-20', author: 'pipeline-ci' },
    ],
    targetDraftVersion: 'v0.9',
  },
  'cnn-base-v1.0': {
    ...DEPLOYED_MODELS[4],
    trainingImages: 4800,
    testImages: 1100,
    activeSince: '2025-01-05',
    metrics: { accuracy: 91.3, precisionMacro: 0.905, recallMacro: 0.898, auc: 0.951 },
    confusionMatrix: buildConfusionMatrix(0.8),
    classPerformance: { glioma: 0.891, meningioma: 0.879, pituitary: 0.902, healthy: 0.94 },
    deploymentHistory: [
      { id: 'evt-1', label: 'trainingCompleted', date: '2025-01-05', author: 'pipeline-ci' },
    ],
    targetDraftVersion: 'v1.1',
  },
}
