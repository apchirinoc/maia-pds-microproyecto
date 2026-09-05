import { useMutation, useQuery } from '@tanstack/react-query'
import {
  classifyImage,
  getActiveModelInfo,
  type ClassifyImageParams,
} from '@/services/classification.service'

export function useClassifyImage() {
  return useMutation({
    mutationFn: (params: ClassifyImageParams) => classifyImage(params),
  })
}

export function useActiveModelInfo() {
  return useQuery({ queryKey: ['model', 'active'], queryFn: getActiveModelInfo })
}
