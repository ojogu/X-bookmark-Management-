import { useNavigate } from 'react-router-dom'

export default function Navbar() {
  const navigate = useNavigate()

  return (
    <nav style={{
      position: 'sticky', top: 0, zIndex: 50, width: '100%',
      background: 'color-mix(in srgb, var(--bg) 80%, transparent)',
      backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
      borderBottom: '0.5px solid var(--border)',
    }}>
      <div style={{
        maxWidth: 1280, margin: '0 auto', padding: '1.25rem 3rem',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <span
          onClick={() => navigate('/')}
          style={{ fontFamily: 'var(--font-serif)', fontSize: 22, color: 'var(--text-primary)', cursor: 'pointer' }}
        >
          Save<span style={{ color: 'var(--accent-mid)' }}>Stack</span>
        </span>

        <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
          {['Features', 'Pricing', 'Blog'].map(link => (
            <a key={link} href="#" style={{
              fontSize: 14, fontWeight: 500, color: 'var(--text-secondary)',
              textDecoration: 'none', transition: 'color 100ms',
            }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
            >{link}</a>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => navigate('/auth')}
            style={{
              fontFamily: 'var(--font-sans)', fontSize: 14, fontWeight: 500,
              color: 'var(--text-primary)', background: 'transparent',
              border: '0.5px solid var(--border-strong)', borderRadius: 'var(--radius-md)',
              padding: '0.55rem 1.25rem', cursor: 'pointer',
            }}>Sign in</button>
          <button
            onClick={() => navigate('/auth')}
            style={{
              fontFamily: 'var(--font-sans)', fontSize: 14, fontWeight: 500,
              color: '#fff', background: 'var(--accent)', border: 'none',
              borderRadius: 'var(--radius-md)', padding: '0.55rem 1.25rem', cursor: 'pointer',
            }}>Get started</button>
        </div>
      </div>
    </nav>
  )
}