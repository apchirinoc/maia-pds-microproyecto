import { beforeEach, expect, it, vi } from 'vitest'

const config = vi.hoisted(() => ({ forceMocks: false }))
vi.mock('@/lib/env', () => ({ env: config }))
import { conOrigenDeDatos, ErrorDeApi, ErrorDeConexion } from './gateway'

beforeEach(() => { config.forceMocks = false })

it('returns the API response unchanged', async () => {
  const data = { predictedClass: 'healthy' }
  const simulated = vi.fn()
  expect(await conOrigenDeDatos(async () => data, simulated)).toBe(data)
  expect(simulated).not.toHaveBeenCalled()
})

it.each([new ErrorDeConexion(), new ErrorDeApi(503, 'Modelo no disponible')])(
  'propagates %s without substituting a simulated result', async (error) => {
    const simulated = vi.fn()
    await expect(conOrigenDeDatos(async () => { throw error }, simulated)).rejects.toBe(error)
    expect(simulated).not.toHaveBeenCalled()
  },
)

it('only simulates when explicitly configured', async () => {
  config.forceMocks = true
  const remote = vi.fn()
  expect(await conOrigenDeDatos(remote, async () => 'demo')).toBe('demo')
  expect(remote).not.toHaveBeenCalled()
})
