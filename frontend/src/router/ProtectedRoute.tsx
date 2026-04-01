import { Navigate } from 'react-router-dom'
import { authStore } from '@/store/auth'

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!authStore.isAuthenticated()) {
    return <Navigate to="/auth" replace />
  }
  return <>{children}</>
}