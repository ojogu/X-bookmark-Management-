import { useNavigate } from 'react-router-dom'

export default function Error404Page() {
  const navigate = useNavigate()

  return (
    <div style={{
      minHeight: '100vh', background: 'var(--bg)',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      padding: '1.5rem',
    }}>
      <span style={{
        fontFamily: 'var(--font-serif)', fontSize: 22,
        fontStyle: 'italic', color: 'var(--text-primary)', marginBottom: '2rem',
      }}>SaveStack</span>

      <div style={{
        textAlign: 'center',
      }}>
        <h1 style={{
          fontFamily: 'var(--font-sans)', fontSize: '4rem', fontWeight: 600,
          color: 'var(--text-primary)', marginBottom: '0.5rem', lineHeight: 1,
        }}>404</h1>
        <p style={{
          fontFamily: 'var(--font-sans)', fontSize: '1.1rem',
          color: 'var(--text-secondary)', marginBottom: '2rem', lineHeight: 1.5,
        }}>Page not found</p>

        <button
          onClick={() => navigate('/')}
          style={{
            fontFamily: 'var(--font-sans)', fontSize: 15, fontWeight: 500,
            color: '#fff', background: 'var(--accent)', border: 'none',
            borderRadius: 'var(--radius-lg)', padding: '0.85rem 2rem', cursor: 'pointer',
          }}>
          Go to Home
        </button>
      </div>
    </div>
  )
}