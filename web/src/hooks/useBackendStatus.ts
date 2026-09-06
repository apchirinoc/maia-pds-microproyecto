import { useCallback, useEffect, useSyncExternalStore } from 'react'
import { env } from '@/lib/env'
import { backendGateway, type InstantaneaBackend } from '@/lib/api/gateway'

/**
 * Estado de conexión con el backend, sincronizado con el gateway.
 *
 * Usa `useSyncExternalStore` porque el estado vive fuera de React: los
 * servicios lo consultan sin ser componentes, y deben ver siempre el mismo
 * valor que la interfaz.
 */
export function useBackendStatus(): InstantaneaBackend & { revalidar: () => void } {
  const instantanea = useSyncExternalStore(
    backendGateway.suscribir,
    backendGateway.obtener,
    backendGateway.obtener,
  )

  useEffect(() => {
    void backendGateway.asegurarSondeo()
  }, [])

  useEffect(() => {
    if (env.healthPollMs <= 0) return
    const intervalo = window.setInterval(() => {
      void backendGateway.revalidar()
    }, env.healthPollMs)
    return () => window.clearInterval(intervalo)
  }, [])

  const revalidar = useCallback(() => {
    void backendGateway.revalidar()
  }, [])

  return { ...instantanea, revalidar }
}
