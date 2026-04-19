import { Navigate } from 'react-router-dom'
import { authStore } from '@/store/auth'

export default function AdminProtectedRoute({ children }: { children: React.ReactNode }) {
  const accessToken = authStore.getAccessToken()
  const refreshToken = authStore.getRefreshToken()
  const adminToken = authStore.getAdminToken()

  const token = adminToken || accessToken || refreshToken

  if (!token) {
    return <Navigate to="/admin/login" replace />
  }

  return <>{children}</>
}