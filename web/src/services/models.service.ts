import type {
  DeployedModel,
  ModelDetail,
  ModelRegistrySummary,
  RegistryModelVersion,
} from '@/types/model'
import {
  DEPLOYED_MODELS,
  MODEL_DETAILS,
  MODEL_REGISTRY_SUMMARY,
  REGISTRY_VERSIONS,
} from '@/mocks/models.mock'
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

export async function getRegistryVersions(): Promise<RegistryModelVersion[]> {
  return conOrigenDeDatos(
    () => apiFetch<RegistryModelVersion[]>('/api/v1/models/registry', { autenticada: true }),
    async () => {
      await randomDelay(300, 550)
      return REGISTRY_VERSIONS
    },
  )
}

export async function activateRegistryVersion(version: string): Promise<RegistryModelVersion> {
  return conOrigenDeDatos(
    () =>
      apiFetch<RegistryModelVersion>(
        `/api/v1/models/registry/${encodeURIComponent(version)}/activate`,
        { method: 'POST', autenticada: true },
      ),
    async () => {
      await randomDelay(500, 900)
      const elegida = REGISTRY_VERSIONS.find((item) => item.version === version) ?? REGISTRY_VERSIONS[0]
      return { ...elegida, alias: 'champion' }
    },
  )
}
