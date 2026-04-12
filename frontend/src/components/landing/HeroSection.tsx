import { useAuth } from '@/hooks/useAuth'

export default function HeroSection() {
  const { loginWithX } = useAuth()

  return (
    <section style={{ padding: '6rem 1.5rem 8rem', position: 'relative', overflow: 'hidden' }}>
      <div style={{ maxWidth: 800, margin: '0 auto', textAlign: 'center' }}>

        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          padding: '5px 14px', borderRadius: 'var(--radius-full)',
          background: 'var(--accent-light)', border: '0.5px solid var(--accent-mid)',
          color: 'var(--accent-mid)', fontSize: 11, fontWeight: 500,
          letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: '2rem',
        }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-mid)', display: 'inline-block' }} />
          Now syncing your X bookmarks
        </div>

        <h1 style={{
          fontFamily: 'var(--font-serif)', fontSize: 'clamp(2.8rem, 6vw, 4.5rem)',
          fontWeight: 400, lineHeight: 1.1, letterSpacing: '-0.5px',
          color: 'var(--text-primary)', marginBottom: '2rem',
        }}>
          Your X bookmarks,<br />
          <em style={{ fontStyle: 'italic', color: 'var(--accent-mid)' }}>finally organized</em>
        </h1>

        <p style={{
          fontFamily: 'var(--font-sans)', fontSize: '1.1rem',
          color: 'var(--text-secondary)', lineHeight: 1.7,
          maxWidth: 560, margin: '0 auto 3rem',
        }}>
          SaveStack connects to your X account and gives your saved posts the home they deserve. No more losing threads or scrolling for hours.
        </p>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, flexWrap: 'wrap' }}>
          <button
            onClick={loginWithX}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              fontFamily: 'var(--font-sans)', fontSize: 15, fontWeight: 500,
              color: '#fff', background: 'var(--accent)', border: 'none',
              borderRadius: 'var(--radius-lg)', padding: '0.85rem 2rem', cursor: 'pointer',
            }}>
            <XLogo />
            Connect with X
          </button>
          <button
            onClick={loginWithX}
            style={{
              fontFamily: 'var(--font-sans)', fontSize: 15, fontWeight: 500,
              color: 'var(--text-secondary)', background: 'transparent',
              border: '0.5px solid var(--border-strong)',
              borderRadius: 'var(--radius-lg)', padding: '0.85rem 2rem', cursor: 'pointer',
            }}>
            See how it works
          </button>
        </div>

      </div>
    </section>
  )
}

function XLogo() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  )
}