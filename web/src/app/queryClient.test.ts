import { MutationObserver, onlineManager } from '@tanstack/react-query'
import { expect, it, vi } from 'vitest'
import { createQueryClient } from './queryClient'

it('reports a failed offline action instead of queuing it for reconnection', async () => {
  const client = createQueryClient()
  onlineManager.setOnline(false)
  const failure = new Error('No connection')
  const send = vi.fn(async () => { throw failure })
  const mutation = new MutationObserver(client, { mutationFn: send })
  try {
    await expect(mutation.mutate()).rejects.toBe(failure)
    expect(send).toHaveBeenCalledOnce()
    expect(mutation.getCurrentResult().isPaused).toBe(false)
  } finally {
    onlineManager.setOnline(true)
    client.clear()
  }
}, 2000)
