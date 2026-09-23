import { QueryClient } from '@tanstack/react-query'

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      // Una acción fallida debe mostrar su error, no quedar en cola hasta
      // recuperar conexión y enviar una imagen que el usuario ya cambió.
      queries: { networkMode: 'always', staleTime: 60_000, retry: 1, refetchOnWindowFocus: false },
      mutations: { networkMode: 'always', retry: false },
    },
  })
}
