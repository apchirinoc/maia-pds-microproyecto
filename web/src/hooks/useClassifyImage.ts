import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  classifyImage,
  getActiveModelInfo,
  type ClassifyImageParams,
} from '@/services/classification.service'

export function useClassifyImage() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (params: ClassifyImageParams) => classifyImage(params),
    onSuccess: () => {
      for (const key of ['dashboard', 'uploads', 'models']) {
        void queryClient.invalidateQueries({ queryKey: [key] })
      }
    },
  })
}

export function useActiveModelInfo() {
  return useQuery({ queryKey: ['model', 'active'], queryFn: getActiveModelInfo })
}
