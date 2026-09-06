import type { DeployedModel, ModelDetail, ModelRegistrySummary } from '@/types/model'
import { DEPLOYED_MODELS, MODEL_DETAILS, MODEL_REGISTRY_SUMMARY } from '@/mocks/models.mock'
import { apiFetch } from '@/lib/api/client'
import { conOrigenDeDatos } from '@/lib/api/gateway'
import { randomDelay } from './delay'

export async function getModelRegistrySummary(): Promise<ModelRegistrySummary> {
  return conOrigenDeDatos(
    () => apiFetch<ModelRegistrySummary>('/api/v1/models/summary', { autenticada: true }),
    async () => {
      await randomDelay(250, 450)
      return MODEL_REGISTRY_SUMMARY
    },
  )
}

export async function getModels(): Promise<DeployedModel[]> {
  return conOrigenDeDatos(
    () => apiFetch<DeployedModel[]>('/api/v1/models', { autenticada: true }),
    async () => {
      await randomDelay(300, 550)
      return DEPLOYED_MODELS
    },
  )
}

export async function getModelById(id: string): Promise<ModelDetail | undefined> {
  return conOrigenDeDatos(
    () => apiFetch<ModelDetail>(`/api/v1/models/${encodeURIComponent(id)}`, { autenticada: true }),
    async () => {
      await randomDelay(300, 550)
      return MODEL_DETAILS[id]
    },
  )
}

export async function deployModel(id: string): Promise<void> {
  return conOrigenDeDatos(
    () =>
      apiFetch<void>(`/api/v1/models/${encodeURIComponent(id)}/deploy`, {
        method: 'POST',
        autenticada: true,
      }),
    async () => {
      await randomDelay(500, 900)
    },
  )
}

export async function revertModel(id: string, targetVersion: string): Promise<void> {
  return conOrigenDeDatos(
    () =>
      apiFetch<void>(`/api/v1/models/${encodeURIComponent(id)}/revert`, {
        method: 'POST',
        json: { targetVersion },
        autenticada: true,
      }),
    async () => {
      await randomDelay(500, 900)
    },
  )
}

export async function uploadModel(file: File): Promise<void> {
  void file
  // La carga de pesos requiere el almacén de artefactos de MLflow (fase 14 del
  // plan). Hasta entonces no se envía nada al servidor: fingir un envío sería
  // anunciar una capacidad inexistente.
  await randomDelay(700, 1200)
}
