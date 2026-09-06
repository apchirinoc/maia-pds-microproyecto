import en from './en.json'
import es from './es.json'

export type Locale = 'es' | 'en'

export const dictionaries = { es, en } as const

export type Dictionary = typeof es
