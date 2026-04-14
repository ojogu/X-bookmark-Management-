import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import client from '@/api/client'
import { authStore } from '@/store/auth'

type ValidationStatus = 'checking' | 'valid' | 'invalid'

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const [validation, setValidation] = useState<ValidationStatus>('checking')

  useEffect(() => {
    async function validateToken() {
      const accessToken = authStore.getAccessToken()
      const refreshToken = authStore.getRefreshToken()

      if (!accessToken && !refreshToken) {
        setValidation('invalid')
        return
      }

      try {
        await client.get('/client/info')
        setValidation('valid')
      } catch {
        authStore.clearTokens()
        setValidation('invalid')
      }
    }

    validateToken()
  }, [])

  if (validation === 'checking') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg">
        <div className="h-px w-48 overflow-hidden rounded-full bg-border-subtle">
          <div
            className="h-full rounded-full bg-brand"
            style={{ animation: 'callback-bar 1.8s ease-in-out infinite' }}
          />
        </div>
        <style>{`
          @keyframes callback-bar {
            0%   { width: 0%;   margin-left: 0; }
            50%  { width: 60%;  margin-left: 20%; }
            100% { width: 0%;   margin-left: 100%; }
          }
        `}</style>
      </div>
    )
  }

  if (validation === 'invalid') {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}