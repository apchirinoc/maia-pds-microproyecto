import type { AdminSession } from '@/types/auth'
import { apiFetch, borrarToken, guardarToken } from '@/lib/api/client'
import { backendGateway, ErrorDeApi } from '@/lib/api/gateway'
import { env } from '@/lib/env'
import { randomDelay } from './delay'

const CLAVE_SESION = 'brainneuroscan.session'

/**
 * Cuenta de demostración del prototipo. Debe coincidir con `DEMO_USERNAME` y
 * `DEMO_PASSWORD` del `.env` del API para que el mismo acceso funcione con y
 * sin backend.
 */
const CUENTA_DEMO = {
  username: 'demo',
  password: 'demo',
  session: { username: 'm.rivera', displayName: 'M. Rivera', role: 'Admin' } satisfies AdminSession,
}

interface RespuestaSesion {
  session: AdminSession
  accessToken: string
  tokenType: string
  expiresInSeconds: number
}

/**
 * Autenticación.
 *
 * Con backend, valida contra la API y guarda el token de acceso. Sin backend,
 * acepta únicamente la cuenta de demostración: una maqueta puede no validar
 * contra un servidor, pero no debe conceder acceso a cualquiera cuando la
 * propia pantalla anuncia «acceso solo para personal autorizado».
 */
export async function login(username: string, password: string): Promise<AdminSession> {
  const { estado } = await backendGateway.asegurarSondeo()

  if (estado === 'online' && !env.forceMocks) {
    try {
      const respuesta = await apiFetch<RespuestaSesion>('/api/v1/auth/login', {
        method: 'POST',
        json: { username, password },
      })
      guardarToken(respuesta.accessToken)
      window.localStorage.setItem(CLAVE_SESION, JSON.stringify(respuesta.session))
      return respuesta.session
    } catch (error) {
      // Un 401 es una respuesta legítima del servidor, no una caída: se propaga
      // como credenciales inválidas en vez de caer a la validación simulada.
      if (error instanceof ErrorDeApi) throw new Error('INVALID_CREDENTIALS')
      backendGateway.marcarCaido()
    }
  }

  await randomDelay(500, 900)
  if (username.trim() !== CUENTA_DEMO.username || password !== CUENTA_DEMO.password) {
    throw new Error('INVALID_CREDENTIALS')
  }
  window.localStorage.setItem(CLAVE_SESION, JSON.stringify(CUENTA_DEMO.session))
  return CUENTA_DEMO.session
}

export async function logout(): Promise<void> {
  const { estado } = await backendGateway.asegurarSondeo()
  if (estado === 'online' && !env.forceMocks) {
    try {
      await apiFetch<void>('/api/v1/auth/logout', { method: 'POST', autenticada: true })
    } catch {
      // Cerrar sesión no puede fallar de cara al usuario: el token se descarta
      // igualmente en el cliente.
    }
  }
  borrarToken()
  window.localStorage.removeItem(CLAVE_SESION)
}

export function getStoredSession(): AdminSession | null {
  const crudo = window.localStorage.getItem(CLAVE_SESION)
  if (!crudo) return null
  try {
    return JSON.parse(crudo) as AdminSession
  } catch {
    return null
  }
}
