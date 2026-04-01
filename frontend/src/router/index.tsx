import { BrowserRouter, Routes, Route } from 'react-router-dom'
import LandingPage from '@/pages/LandingPage'
import AuthPage from '@/pages/AuthPage'
import CallbackPage from '@/pages/CallbackPage'
import DashboardPage from '@/pages/DashboardPage'
import ProtectedRoute from '@/router/ProtectedRoute'

export default function Router() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/auth" element={<AuthPage />} />
        <Route path="/dashboard" element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        } />
        <Route path="/callback" element={<CallbackPage />} />
      </Routes>
    </BrowserRouter>
  )
}