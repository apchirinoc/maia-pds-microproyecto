import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  deployModel,
  getModelById,
  getModelRegistrySummary,
  getModels,
  revertModel,
  uploadModel,
} from '@/services/models.service'

export function useModelRegistrySummary() {
  return useQuery({ queryKey: ['models', 'summary'], queryFn: getModelRegistrySummary })
}

export function useModels() {
  return useQuery({ queryKey: ['models', 'list'], queryFn: getModels })
}

export function useModelDetail(id: string | undefined) {
  return useQuery({
    queryKey: ['models', 'detail', id],
    queryFn: () => getModelById(id as string),
    enabled: Boolean(id),
  })
}

export function useRevertModel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, targetVersion }: { id: string; targetVersion: string }) =>
      revertModel(id, targetVersion),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['models'] })
    },
  })
}

export function useDeployModel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deployModel(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['models'] })
    },
  })
}

export function useUploadModel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => uploadModel(file),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['models'] })
    },
  })
}
