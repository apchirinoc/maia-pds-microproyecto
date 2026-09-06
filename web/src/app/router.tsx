import { Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from '@/components/layout/ProtectedRoute'
import { DashboardPage } from '@/pages/DashboardPage'
import { AnalyzeImagePage } from '@/pages/AnalyzeImagePage'
import { LoginPage } from '@/pages/LoginPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { ModelManagementPage } from '@/pages/admin/ModelManagementPage'
import { ModelDetailPage } from '@/pages/admin/ModelDetailPage'
import { UploadHistoryPage } from '@/pages/admin/UploadHistoryPage'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/analyze" element={<AnalyzeImagePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/admin/models"
        element={
          <ProtectedRoute>
            <ModelManagementPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/models/:id"
        element={
          <ProtectedRoute>
            <ModelDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/history"
        element={
          <ProtectedRoute>
            <UploadHistoryPage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
