/** Cliente HTTP: propaga errores de red y del servidor a la interfaz. */

import { env } from '@/lib/env'
import { ErrorDeApi, ErrorDeConexion } from './gateway'

const CLAVE_TOKEN = 'brainneuroscan.token'

export function guardarToken(token: string): void {
  window.localStorage.setItem(CLAVE_TOKEN, token)
}

export function borrarToken(): void {
  window.localStorage.removeItem(CLAVE_TOKEN)
}

export function obtenerToken(): string | null {
  return window.localStorage.getItem(CLAVE_TOKEN)
}

const oyentesSesionExpirada = new Set<() => void>()

/**
 * Avisa cuando el servidor rechaza la sesión.
 *
 * Sin esto, un token caducado dejaba las vistas protegidas vacías: la interfaz
 * seguía creyéndose autenticada porque la sesión estaba en `localStorage`, y
 * cada consulta fallaba con 401 en silencio.
 */
export function alExpirarSesion(oyente: () => void): () => void {
  oyentesSesionExpirada.add(oyente)
  return () => oyentesSesionExpirada.delete(oyente)
}

function notificarSesionExpirada(): void {
  borrarToken()
  for (const avisar of oyentesSesionExpirada) avisar()
}

interface OpcionesPeticion extends Omit<RequestInit, 'body'> {
  /** Cuerpo JSON; se serializa y se le pone la cabecera correspondiente. */
  json?: unknown
  /** Cuerpo ya construido (por ejemplo `FormData` para subir la imagen). */
  body?: BodyInit
  /** Adjunta el token de sesión si existe. */
  autenticada?: boolean
  timeoutMs?: number
}

async function extraerDetalle(respuesta: Response): Promise<string | null> {
  try {
    const cuerpo = await respuesta.json()
    // La API normaliza sus errores según RFC 7807.
    if (typeof cuerpo?.detail === 'string') return cuerpo.detail
    if (typeof cuerpo?.title === 'string') return cuerpo.title
    return null
  } catch {
    return null
  }
}

async function ejecutar(ruta: string, opciones: OpcionesPeticion): Promise<Response> {
  const { json, autenticada = false, timeoutMs = env.apiTimeoutMs, headers, ...resto } = opciones

  const cabeceras = new Headers(headers)
  cabeceras.set('Accept', 'application/json')
  if (json !== undefined) cabeceras.set('Content-Type', 'application/json')
  if (autenticada) {
    const token = obtenerToken()
    if (token !== null) cabeceras.set('Authorization', `Bearer ${token}`)
  }

  const controlador = new AbortController()
  const temporizador = window.setTimeout(() => controlador.abort(), timeoutMs)

  try {
    return await fetch(`${env.apiBaseUrl}${ruta}`, {
      ...resto,
      headers: cabeceras,
      signal: controlador.signal,
      body: json !== undefined ? JSON.stringify(json) : resto.body,
    })
  } catch (error) {
    // `fetch` sólo rechaza por red, CORS o cancelación: nunca por código HTTP.
    throw new ErrorDeConexion(error)
  } finally {
    window.clearTimeout(temporizador)
  }
}

export async function apiFetch<T>(ruta: string, opciones: OpcionesPeticion = {}): Promise<T> {
  const respuesta = await ejecutar(ruta, opciones)
  if (!respuesta.ok) {
    if (respuesta.status === 401 && opciones.autenticada === true) {
      notificarSesionExpirada()
    }
    throw new ErrorDeApi(respuesta.status, await extraerDetalle(respuesta))
  }
  if (respuesta.status === 204) return undefined as T

  // Un 200 que no es JSON no viene de la API: lo típico es un proxy o un
  // servidor de estáticos devolviendo el index.html de la SPA. Se trata como
  // fallo de conexión y se muestra el error al usuario.
  const tipo = respuesta.headers.get('Content-Type') ?? ''
  if (!tipo.includes('json')) {
    throw new ErrorDeConexion(`La API respondió ${tipo || 'sin tipo'} en lugar de JSON`)
  }

  try {
    return (await respuesta.json()) as T
  } catch (error) {
    throw new ErrorDeConexion(error)
  }
}

export async function apiFetchBlob(ruta: string, opciones: OpcionesPeticion = {}): Promise<Blob> {
  const respuesta = await ejecutar(ruta, opciones)
  if (!respuesta.ok) {
    if (respuesta.status === 401 && opciones.autenticada === true) {
      notificarSesionExpirada()
    }
    throw new ErrorDeApi(respuesta.status, await extraerDetalle(respuesta))
  }
  return respuesta.blob()
}
