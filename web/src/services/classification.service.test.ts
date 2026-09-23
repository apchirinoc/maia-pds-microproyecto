import { afterEach, expect, it, vi } from 'vitest'
import { classifyImage } from './classification.service'

vi.mock('@/lib/env', () => ({ env: { forceMocks: false, apiBaseUrl: 'http://test' } }))
afterEach(() => vi.unstubAllGlobals())

it('sends the selected bytes as multipart, without a class hint', async () => {
  vi.stubGlobal('window', { setTimeout, clearTimeout })
  const response = { predictedClass: 'glioma', simulatedInference: false }
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(Response.json(response))
  vi.stubGlobal('fetch', fetchMock)
  const file = new File(['actual image bytes'], 'selected.png', { type: 'image/png' })
  const result = await classifyImage({ countryCode: 'CO', requestId: 1, file })
  expect(result).toEqual(response)
  const [url, options] = fetchMock.mock.calls[0]
  expect(url).toBe('http://test/api/v1/classifications')
  expect(options?.method).toBe('POST')
  const body = options?.body
  expect(body).toBeInstanceOf(FormData)
  if (!(body instanceof FormData)) throw new Error('Expected multipart')
  expect(body.get('countryCode')).toBe('CO')
  expect(body.get('explain')).toBe('false')
  expect(body.has('hint')).toBe(false)
  const sent = body.get('file')
  if (!(sent instanceof File)) throw new Error('Expected a file')
  expect(await sent.text()).toBe(await file.text())
  expect(sent.name).toBe('selected.png')
  expect(new Headers(options?.headers).has('Content-Type')).toBe(false)
})
