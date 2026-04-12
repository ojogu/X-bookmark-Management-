import { BrowserRouter, Routes, Route } from 'react-router-dom'
import LandingPage from '@/pages/LandingPage'
import CallbackPage from '@/pages/CallbackPage'
import DashboardPage from '@/pages/DashboardPage'
import Error500Page from '@/pages/Error500Page'
import Error404Page from '@/pages/Error404Page'
import ProtectedRoute from '@/router/ProtectedRoute'

export default function Router() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard" element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        } />
        <Route path="/callback" element={<CallbackPage />} />
        <Route path="/error/500" element={<Error500Page />} />
        <Route path="/error/404" element={<Error404Page />} />
        <Route path="*" element={<Error404Page />} />
      </Routes>
    </BrowserRouter>
  )
}