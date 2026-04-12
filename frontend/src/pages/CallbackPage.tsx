import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authStore } from '@/store/auth'

type Status = 'loading' | 'error'

const messages = [
  'Connecting your X account...',
  'Reading your saved posts...',
  'Building your library...',
  'Almost done...',
]

export default function CallbackPage() {
  const navigate = useNavigate()
  const [status, setStatus] = useState<Status>('loading')
  const [messageIndex, setMessageIndex] = useState(0)

  useEffect(() => {
    if (authStore.isAuthenticated()) {
      navigate('/dashboard', { replace: true })
      return
    }
  }, [navigate])

  useEffect(() => {
    const interval = setInterval(() => {
      setMessageIndex(i => (i + 1) % messages.length)
    }, 1800)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const accessToken = params.get('access-token')
    const refreshToken = params.get('refresh-token')
    const error = params.get('error')

    if (error || !accessToken || !refreshToken) {
      setStatus('error')
      return
    }

    authStore.setTokens(accessToken, refreshToken)

    // Clean tokens from URL then redirect
    window.history.replaceState({}, '', '/dashboard')
    setTimeout(() => navigate('/dashboard', { replace: true }), 800)
  }, [navigate])

  return (
    <div style={{
      minHeight: '100vh', background: 'var(--bg)',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      gap: '2rem',
    }}>

      {/* Logo */}
      <span style={{
        fontFamily: 'var(--font-serif)', fontSize: 24,
        fontStyle: 'italic', color: 'var(--text-primary)',
      }}>SaveStack</span>

      {status === 'loading' && (
        <>
          {/* Progress bar */}
          <div style={{
            width: 200, height: 2,
            background: 'var(--border)', borderRadius: 'var(--radius-full)',
            overflow: 'hidden',
          }}>
            <div style={{
              height: '100%', background: 'var(--accent-mid)',
              borderRadius: 'var(--radius-full)',
              animation: 'pulse-bar 1.5s ease-in-out infinite',
            }} />
          </div>

          {/* Status message */}
          <p style={{
            fontSize: 14, color: 'var(--text-secondary)',
            fontFamily: 'var(--font-sans)', textAlign: 'center',
            transition: 'opacity 300ms',
          }}>
            {messages[messageIndex]}
          </p>

          <p style={{
            fontSize: 12, color: 'var(--text-muted)',
            fontFamily: 'var(--font-sans)', textAlign: 'center',
            maxWidth: 300, lineHeight: 1.6,
          }}>
            First-time import may take a moment depending on how many posts you've saved.
          </p>
        </>
      )}

      {status === 'error' && (
        <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
          <p style={{ fontSize: 14, color: '#E24B4A', fontFamily: 'var(--font-sans)' }}>
            Something went wrong. Please try again.
          </p>
          <button
            onClick={() => navigate('/')}
            style={{
              fontFamily: 'var(--font-sans)', fontSize: 14, fontWeight: 500,
              color: '#fff', background: 'var(--accent)', border: 'none',
              borderRadius: 'var(--radius-md)', padding: '0.6rem 1.5rem', cursor: 'pointer',
            }}>
            Back to Home
          </button>
        </div>
      )}

      <style>{`
        @keyframes pulse-bar {
          0% { width: 0%; margin-left: 0; }
          50% { width: 70%; margin-left: 15%; }
          100% { width: 0%; margin-left: 100%; }
        }
      `}</style>

    </div>
  )
}