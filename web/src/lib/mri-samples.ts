import type { TumorClass } from '@/types/classification'

export const SAMPLE_IMAGES_BY_CLASS: Record<TumorClass, { url: string; fileName: string }> = {
  glioma: {
    url: '/samples/Te-gl_0023.jpg',
    fileName: 'Te-gl_0023.jpg',
  },
  meningioma: {
    url: '/samples/Te-me_0015.jpg',
    fileName: 'Te-me_0015.jpg',
  },
  pituitary: {
    url: '/samples/Te-pi_0204.jpg',
    fileName: 'Te-pi_0204.jpg',
  },
  healthy: {
    url: '/samples/Te-no_0109.jpg',
    fileName: 'Te-no_0109.jpg',
  },
}
