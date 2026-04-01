import { useAuth } from '@/hooks/useAuth'
import { useState, useEffect } from 'react'

type AuthState = 'idle' | 'loading' | 'error'

export default function AuthPage() {
  const [authState, setAuthState] = useState<AuthState>('idle')
  const { loginWithX } = useAuth()

  // Check if backend redirected here with an error
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('error')) {
      setAuthState('error')
      // Clean the error from the URL
      window.history.replaceState({}, '', '/auth')
    }
  }, [])

  async function handleConnect() {
    try {
      setAuthState('loading')
      await loginWithX()
    } catch {
      setAuthState('error')
    }
  }


  return (
    <div style={{
      minHeight: '100vh', background: 'var(--bg)',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      padding: '1.5rem',
    }}>

      <header style={{
        position: 'fixed', top: 0, width: '100%',
        height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'color-mix(in srgb, var(--bg) 80%, transparent)',
        backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
        zIndex: 50,
      }}>
        <span style={{
          fontFamily: 'var(--font-serif)', fontSize: 22,
          fontStyle: 'italic', color: 'var(--text-primary)',
        }}>SaveStack</span>
      </header>

      <main style={{
        width: '100%', maxWidth: 400,
        display: 'flex', flexDirection: 'column', alignItems: 'center',
      }}>
        <div style={{
          width: '100%', background: 'var(--bg-card)',
          borderRadius: 'var(--radius-xl)', padding: '2.5rem',
          border: '0.5px solid var(--border)',
          display: 'flex', flexDirection: 'column', alignItems: 'center',
        }}>

          <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
            <h1 style={{
              fontFamily: 'var(--font-serif)', fontSize: '2rem',
              fontStyle: 'italic', fontWeight: 400,
              color: 'var(--text-primary)', marginBottom: '1rem', lineHeight: 1.2,
            }}>
              Connect your X account
            </h1>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
              SaveStack reads your bookmarks. It never posts, follows, or modifies anything on your behalf.
            </p>
          </div>

          <button
            onClick={handleConnect}
            disabled={authState === 'loading'}
            style={{
              width: '100%', background: 'var(--accent)', color: '#fff',
              border: 'none', borderRadius: 'var(--radius-lg)',
              padding: '1rem 1.5rem', cursor: authState === 'loading' ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
              fontFamily: 'var(--font-sans)', fontSize: 15, fontWeight: 500,
              opacity: authState === 'loading' ? 0.7 : 1,
              transition: 'opacity 150ms',
            }}
          >
            {authState === 'loading' ? (
              <><Spinner /> Connecting...</>
            ) : (
              <><XLogo /> Continue with X</>
            )}
          </button>

          {authState === 'error' && (
            <div style={{
              marginTop: '1rem', display: 'flex', alignItems: 'center', gap: 6,
              color: '#E24B4A', fontSize: 13, fontWeight: 500,
            }}>
              <span>⚠</span>
              Authentication failed. Please try again.
            </div>
          )}

          <div style={{ marginTop: '2rem', textAlign: 'center' }}>
            <p style={{
              fontSize: 11, color: 'var(--text-muted)',
              letterSpacing: '0.05em', textTransform: 'uppercase', lineHeight: 1.8,
            }}>
              By continuing, you agree to our{' '}
              <a href="#" style={{ color: 'var(--text-muted)', textDecoration: 'underline' }}>Terms of Service</a>
              {' '}&{' '}
              <a href="#" style={{ color: 'var(--text-muted)', textDecoration: 'underline' }}>Privacy Policy</a>
            </p>
          </div>

        </div>

        <div style={{
          marginTop: '3rem', display: 'flex', flexDirection: 'column',
          alignItems: 'center', gap: '1rem', opacity: 0.4,
        }}>
          <div style={{ width: 1, height: 48, background: 'var(--border-strong)' }} />
          <span style={{
            fontFamily: 'var(--font-serif)', fontSize: 16,
            fontStyle: 'italic', color: 'var(--text-secondary)',
          }}>The Digital Archivist</span>
        </div>
      </main>

      <footer style={{
        position: 'fixed', bottom: 0, width: '100%',
        paddingBottom: '2rem',
        display: 'flex', justifyContent: 'center', gap: '1.5rem', flexWrap: 'wrap',
      }}>
        {['© 2024 SaveStack', 'Terms of Service', 'Privacy Policy', 'Help Center'].map(item => (
          <span key={item} style={{
            fontSize: 11, color: 'var(--text-muted)',
            letterSpacing: '0.05em', textTransform: 'uppercase',
          }}>{item}</span>
        ))}
      </footer>

    </div>
  )
}

function XLogo() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  )
}

function Spinner() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
      style={{ animation: 'spin 0.8s linear infinite' }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
    </svg>
  )
}