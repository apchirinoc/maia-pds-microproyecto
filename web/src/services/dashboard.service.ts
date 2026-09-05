import {
  DASHBOARD_KPIS,
  DATASET_SAMPLES,
  MONTHLY_UPLOADS,
  RECENT_UPLOADS_PROFILE,
  TRAINING_CLASS_DISTRIBUTION,
  type DashboardKpis,
  type DatasetSample,
  type RecentUploadsProfilePoint,
} from '@/mocks/dashboard.mock'
import { COUNTRY_UPLOAD_STATS } from '@/mocks/countries.mock'
import { apiFetch } from '@/lib/api/client'
import { conOrigenDeDatos } from '@/lib/api/gateway'
import type { TumorClass } from '@/types/classification'
import type { CountryUploadStat } from '@/types/country'
import { randomDelay } from './delay'

/**
 * Servicios del panel.
 *
 * Cada función declara sus dos orígenes: la API cuando hay backend, y los datos
 * simulados cuando no lo hay. `conOrigenDeDatos` decide cuál se usa; ni los
 * hooks ni los componentes conocen esa decisión.
 */

export async function getDashboardKpis(): Promise<DashboardKpis> {
  return conOrigenDeDatos(
    () => apiFetch<DashboardKpis>('/api/v1/dashboard/kpis'),
    async () => {
      await randomDelay(250, 500)
      return DASHBOARD_KPIS
    },
  )
}

export async function getTrainingClassDistribution(): Promise<Record<TumorClass, number>> {
  return conOrigenDeDatos(
    () => apiFetch<Record<TumorClass, number>>('/api/v1/dashboard/training-distribution'),
    async () => {
      await randomDelay(250, 500)
      return TRAINING_CLASS_DISTRIBUTION
    },
  )
}

export async function getMonthlyUploads(): Promise<{ month: string; uploads: number }[]> {
  return conOrigenDeDatos(
    () => apiFetch<{ month: string; uploads: number }[]>('/api/v1/dashboard/uploads-by-month'),
    async () => {
      await randomDelay(250, 500)
      return MONTHLY_UPLOADS
    },
  )
}

export async function getRecentUploadsProfile(): Promise<RecentUploadsProfilePoint[]> {
  return conOrigenDeDatos(
    () => apiFetch<RecentUploadsProfilePoint[]>('/api/v1/dashboard/recent-profile'),
    async () => {
      await randomDelay(250, 500)
      return RECENT_UPLOADS_PROFILE
    },
  )
}

export async function getCountryUploadStats(): Promise<CountryUploadStat[]> {
  return conOrigenDeDatos(
    () => apiFetch<CountryUploadStat[]>('/api/v1/dashboard/uploads-by-country'),
    async () => {
      await randomDelay(300, 600)
      return COUNTRY_UPLOAD_STATS
    },
  )
}

export async function getDatasetSamples(): Promise<DatasetSample[]> {
  return conOrigenDeDatos(
    () => apiFetch<DatasetSample[]>('/api/v1/dashboard/dataset-samples'),
    async () => {
      await randomDelay(150, 300)
      return DATASET_SAMPLES
    },
  )
}
