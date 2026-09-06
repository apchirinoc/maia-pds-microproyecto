import { useQuery } from '@tanstack/react-query'
import {
  getCountryUploadStats,
  getDashboardKpis,
  getDatasetSamples,
  getMonthlyUploads,
  getRecentUploadsProfile,
  getTrainingClassDistribution,
} from '@/services/dashboard.service'

export function useDashboardKpis() {
  return useQuery({ queryKey: ['dashboard', 'kpis'], queryFn: getDashboardKpis })
}

export function useTrainingClassDistribution() {
  return useQuery({
    queryKey: ['dashboard', 'training-distribution'],
    queryFn: getTrainingClassDistribution,
  })
}

export function useMonthlyUploads() {
  return useQuery({ queryKey: ['dashboard', 'monthly-uploads'], queryFn: getMonthlyUploads })
}

export function useRecentUploadsProfile() {
  return useQuery({ queryKey: ['dashboard', 'recent-profile'], queryFn: getRecentUploadsProfile })
}

export function useCountryUploadStats() {
  return useQuery({ queryKey: ['dashboard', 'country-uploads'], queryFn: getCountryUploadStats })
}

export function useDatasetSamples() {
  return useQuery({ queryKey: ['dashboard', 'dataset-samples'], queryFn: getDatasetSamples })
}
