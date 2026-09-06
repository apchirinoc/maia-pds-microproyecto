/**
 * Acceso tipado a la configuración de entorno.
 *
 * Vite inyecta en tiempo de build las variables con prefijo `VITE_`. Este
 * módulo es el único punto donde se leen: el resto del código recibe valores ya
 * validados y con tipo, nunca `string | undefined`.
 */

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
  apiBaseUrl: normalizarBase(texto(import.meta.env.VITE_API_BASE_URL, 'http://localhost:8000')),
  apiTimeoutMs: entero(import.meta.env.VITE_API_TIMEOUT_MS, 6000),
  healthTimeoutMs: entero(import.meta.env.VITE_HEALTH_TIMEOUT_MS, 2500),
  healthPollMs: entero(import.meta.env.VITE_HEALTH_POLL_MS, 30000),
  forceMocks: booleano(import.meta.env.VITE_FORCE_MOCKS, false),
  isDev: import.meta.env.DEV,
} as const
