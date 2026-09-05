import type { TumorClass } from '@/types/classification'

export interface DashboardKpis {
  trainingImages: number
  trainingImagesBreakdown: string
  modelAccuracy: number
  modelAccuracyDeltaPts: number
  userPredictions: number
  userPredictionsThisMonth: number
  activeCountries: number
  activeContinents: number
}

export const DASHBOARD_KPIS: DashboardKpis = {
  trainingImages: 7023,
  trainingImagesBreakdown: '5 712 train · 1 311 test',
  modelAccuracy: 98.4,
  modelAccuracyDeltaPts: 1.2,
  userPredictions: 12847,
  userPredictionsThisMonth: 1380,
  activeCountries: 28,
  activeContinents: 4,
}

export const TRAINING_CLASS_DISTRIBUTION: Record<TumorClass, number> = {
  glioma: 1621,
  meningioma: 1645,
  pituitary: 1757,
  healthy: 2000,
}

export const MONTHLY_UPLOADS: { month: string; uploads: number }[] = [
  { month: 'S', uploads: 520 },
  { month: 'O', uploads: 610 },
  { month: 'N', uploads: 690 },
  { month: 'D', uploads: 740 },
  { month: 'E', uploads: 820 },
  { month: 'F', uploads: 880 },
  { month: 'M', uploads: 940 },
  { month: 'A', uploads: 1010 },
  { month: 'M', uploads: 1080 },
  { month: 'J', uploads: 1150 },
  { month: 'J', uploads: 1220 },
  { month: 'A', uploads: 1300 },
]

export interface RecentUploadsProfilePoint {
  axis: TumorClass | 'confidence' | 'volume'
  value: number
}

export const RECENT_UPLOADS_PROFILE: RecentUploadsProfilePoint[] = [
  { axis: 'glioma', value: 78 },
  { axis: 'meningioma', value: 62 },
  { axis: 'pituitary', value: 55 },
  { axis: 'healthy', value: 90 },
  { axis: 'confidence', value: 94 },
  { axis: 'volume', value: 70 },
]

export interface DatasetSample {
  tumorClass: TumorClass
  fileName: string
}

export const DATASET_SAMPLES: DatasetSample[] = [
  { tumorClass: 'glioma', fileName: 'Te-gl_0023.jpg' },
  { tumorClass: 'meningioma', fileName: 'Te-me_0015.jpg' },
  { tumorClass: 'pituitary', fileName: 'Te-pi_0204.jpg' },
  { tumorClass: 'healthy', fileName: 'Te-no_0109.jpg' },
]

export const KAGGLE_DATASET_URL =
  'https://www.kaggle.com/datasets/masoudnickparvar/brain-tumor-mri-dataset'
