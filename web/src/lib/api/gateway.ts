/** La API es el origen normal. La simulación requiere VITE_FORCE_MOCKS=true. */

import { env } from '@/lib/env'

export type EstadoBackend = 'checking' | 'online' | 'offline'

export interface InfoBackend {
  appName: string
  apiVersion: string
  environment: string
  dataSource: string
  simulatedInference: boolean
  modelVersion: string
  preprocessLabel: string
}

export interface InstantaneaBackend {
  estado: EstadoBackend
  latenciaMs: number | null
  info: InfoBackend | null
  comprobadoEn: number | null
}

/** Error de conectividad que se propaga a la pantalla. */
export class ErrorDeConexion extends Error {
  constructor(causa?: unknown) {
    super('No hay conexión con el backend')
    this.name = 'ErrorDeConexion'
    this.cause = causa
  }
}

/** Error devuelto por el backend (respondió, pero con un código de error). */
export class ErrorDeApi extends Error {
  readonly status: number
  readonly detalle: string | null

  constructor(status: number, detalle: string | null) {
    super(detalle ?? `La API respondió ${status}`)
    this.name = 'ErrorDeApi'
    this.status = status
    this.detalle = detalle
  }
}

let instantanea: InstantaneaBackend = {
  estado: env.forceMocks ? 'offline' : 'checking',
  latenciaMs: null,
  info: null,
  comprobadoEn: null,
}

const suscriptores = new Set<() => void>()
let sondaEnCurso: Promise<InstantaneaBackend> | null = null

function publicar(siguiente: InstantaneaBackend): void {
  instantanea = siguiente
  for (const notificar of suscriptores) notificar()
}

async function pedirConTiempoLimite(ruta: string, timeoutMs: number): Promise<Response> {
  const controlador = new AbortController()
  const temporizador = window.setTimeout(() => controlador.abort(), timeoutMs)
  try {
    return await fetch(`${env.apiBaseUrl}${ruta}`, {
      signal: controlador.signal,
      headers: { Accept: 'application/json' },
    })
  } finally {
    window.clearTimeout(temporizador)
  }
}

/** Ejecuta la sonda de salud y actualiza el estado. */
async function sondear(): Promise<InstantaneaBackend> {
  if (env.forceMocks) {
    publicar({ estado: 'offline', latenciaMs: null, info: null, comprobadoEn: Date.now() })
    return instantanea
  }

  const inicio = performance.now()
  try {
    const salud = await pedirConTiempoLimite('/health', env.healthTimeoutMs)
    if (!salud.ok) throw new ErrorDeConexion(`/health respondió ${salud.status}`)

    // No basta con un 200: hay que comprobar que quien responde es NUESTRA API.
    // Con `VITE_API_BASE_URL=/` la sonda va al propio origen, y el nginx que
    // sirve la interfaz también expone un `/health` para su propia liveness.
    // Sin esta comprobación el frontend se creía conectado, no caía a datos
    // simulados, y las peticiones a /api/v1/* recibían el index.html de la SPA.
    const cuerpo = await salud.json().catch(() => null)
    if (cuerpo === null || (cuerpo as { status?: string }).status !== 'ok') {
      throw new ErrorDeConexion('La respuesta de /health no procede de la API')
    }

    const latenciaMs = Math.round(performance.now() - inicio)

    let info: InfoBackend | null = null
    try {
      const meta = await pedirConTiempoLimite('/api/v1/meta', env.healthTimeoutMs)
      if (meta.ok) info = (await meta.json()) as InfoBackend
    } catch {
      // El servicio está vivo aunque /meta falle: no degrada el estado.
    }

    publicar({ estado: 'online', latenciaMs, info, comprobadoEn: Date.now() })
  } catch {
    publicar({ estado: 'offline', latenciaMs: null, info: null, comprobadoEn: Date.now() })
  }
  return instantanea
}

export const backendGateway = {
  obtener(): InstantaneaBackend {
    return instantanea
  },

  suscribir(notificar: () => void): () => void {
    suscriptores.add(notificar)
    return () => suscriptores.delete(notificar)
  },

  /** Lanza la sonda una sola vez aunque la llamen varias consultas a la vez. */
  asegurarSondeo(): Promise<InstantaneaBackend> {
    if (instantanea.estado !== 'checking' && sondaEnCurso === null) {
      return Promise.resolve(instantanea)
    }
    if (sondaEnCurso === null) {
      sondaEnCurso = sondear().finally(() => {
        sondaEnCurso = null
      })
    }
    return sondaEnCurso
  },

  /** Fuerza una nueva comprobación (botón «reintentar» y sondeo periódico). */
  revalidar(): Promise<InstantaneaBackend> {
    if (sondaEnCurso !== null) return sondaEnCurso
    sondaEnCurso = sondear().finally(() => {
      sondaEnCurso = null
    })
    return sondaEnCurso
  },

  /** Marca el backend como caído en cuanto una petición falla por red. */
  marcarCaido(): void {
    if (instantanea.estado === 'offline') return
    publicar({ estado: 'offline', latenciaMs: null, info: null, comprobadoEn: Date.now() })
  },
}

/** Selecciona la demostración explícita o la API, sin sustitución ante errores. */
export async function conOrigenDeDatos<T>(
  remoto: () => Promise<T>,
  simulado: () => Promise<T>,
): Promise<T> {
  if (env.forceMocks) return simulado()

  try {
    return await remoto()
  } catch (error) {
    if (error instanceof ErrorDeConexion) {
      backendGateway.marcarCaido()
    }
    throw error
  }
}
