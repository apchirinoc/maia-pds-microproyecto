import type { TumorClass } from '@/types/classification'

export const TUMOR_CLASS_COLORS: Record<TumorClass, string> = {
  glioma: '#4f46e5',
  meningioma: '#059669',
  pituitary: '#d97706',
  healthy: '#0891b2',
}

export const TUMOR_CLASS_BADGE_VARIANT: Record<TumorClass, 'info' | 'success' | 'warning' | 'neutral'> = {
  glioma: 'info',
  meningioma: 'success',
  pituitary: 'warning',
  healthy: 'neutral',
}

export const CHART_MUTED_COLOR = '#71717a'
export const CHART_GRID_COLOR = '#a1a1aa33'
