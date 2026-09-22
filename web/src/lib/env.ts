/**
 * Acceso tipado a la configuración de entorno.
 *
 * Soporta configuración tanto en tiempo de build (Vite import.meta.env)
 * como en tiempo de ejecución de contenedor (window.__ENV__ inyectado por nginx/entrypoint).
 */

declare global {
  interface Window {
    __ENV__?: Record<string, string | undefined>
  }
}

function obtenerVariable(clave: string, valorBuild: string | undefined): string | undefined {
  if (typeof window !== 'undefined' && window.__ENV__ && window.__ENV__[clave] !== undefined) {
    const val = window.__ENV__[clave]
    if (val !== undefined && val !== '') return val
  }
  return valorBuild
}

function texto(valor: string | undefined, porDefecto: string): string {
  const limpio = valor?.trim()
  return limpio === undefined || limpio === '' ? porDefecto : limpio
}

function entero(valor: string | undefined, porDefecto: number): number {
  const numero = Number.parseInt(texto(valor, ''), 10)
  return Number.isFinite(numero) && numero >= 0 ? numero : porDefecto
}

function booleano(valor: string | undefined, porDefecto: boolean): boolean {
  const limpio = texto(valor, '').toLowerCase()
  if (limpio === 'true' || limpio === '1') return true
  if (limpio === 'false' || limpio === '0') return false
  return porDefecto
}

/** Normaliza la base para poder concatenar rutas sin barras duplicadas. */
function normalizarBase(base: string): string {
  return base === '/' ? '' : base.replace(/\/+$/, '')
}

export const env = {
  apiBaseUrl: normalizarBase(
    texto(
      obtenerVariable('VITE_API_BASE_URL', import.meta.env.VITE_API_BASE_URL) ||
        obtenerVariable('API_URL', undefined),
      'http://localhost:8000'
    )
  ),
  apiTimeoutMs: entero(
    obtenerVariable('VITE_API_TIMEOUT_MS', import.meta.env.VITE_API_TIMEOUT_MS),
    6000
  ),
  healthTimeoutMs: entero(
    obtenerVariable('VITE_HEALTH_TIMEOUT_MS', import.meta.env.VITE_HEALTH_TIMEOUT_MS),
    2500
  ),
  healthPollMs: entero(
    obtenerVariable('VITE_HEALTH_POLL_MS', import.meta.env.VITE_HEALTH_POLL_MS),
    30000
  ),
  forceMocks: booleano(
    obtenerVariable('VITE_FORCE_MOCKS', import.meta.env.VITE_FORCE_MOCKS),
    false
  ),
  isDev: import.meta.env.DEV,
} as const

