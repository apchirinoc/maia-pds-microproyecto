import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { RecordGroundTruthInput, UploadHistoryFilters } from '@/types/upload'
import {
  addUploadsToDataset,
  exportUploadHistoryCsv,
  getUploadHistory,
  getUploadHistorySummary,
  recordGroundTruth,
} from '@/services/uploads.service'

export function useUploadHistorySummary() {
  return useQuery({ queryKey: ['uploads', 'summary'], queryFn: getUploadHistorySummary })
}

export function useUploadHistory(filters: UploadHistoryFilters) {
  return useQuery({
    queryKey: ['uploads', 'history', filters],
    queryFn: () => getUploadHistory(filters),
  })
}

export function useExportUploadHistoryCsv() {
  return useMutation({ mutationFn: exportUploadHistoryCsv })
}

/**
 * Registra el diagnóstico confirmado de una carga e invalida todas las
 * consultas de cargas: así se refrescan a la vez la tabla del histórico y los
 * dos KPI de verdad de campo, que el servicio recalcula desde los datos.
 */
export function useRecordGroundTruth() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: RecordGroundTruthInput) => recordGroundTruth(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['uploads'] })
    },
  })
}

export function useAddUploadsToDataset() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (ids: string[]) => addUploadsToDataset(ids),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['uploads'] })
    },
  })
}
