export default function Footer() {
  return (
    <footer style={{
      background: 'var(--bg-subtle)',
      borderTop: '0.5px solid var(--border)',
    }}>
      <div style={{
        maxWidth: 1280, margin: '0 auto',
        padding: '3rem 2rem',
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', flexWrap: 'wrap', gap: '1.5rem',
      }}>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={{
            fontFamily: 'var(--font-serif)', fontSize: 20,
            fontStyle: 'italic', color: 'var(--text-primary)',
            display: 'block',
          }}>
            SaveStack
          </span>
          <span style={{
            fontSize: 11, color: 'var(--text-muted)',
            letterSpacing: '0.06em', textTransform: 'uppercase',
            display: 'block',
          }}>
            © 2026 SaveStack · Built by Ojogu
          </span>
        </div>

        <div style={{ display: 'flex', gap: '2.5rem' }}>
          {['Terms', 'Privacy', 'Support'].map(link => (
            <a key={link} href="#" style={{
              fontSize: 11, color: 'var(--text-muted)',
              letterSpacing: '0.06em', textTransform: 'uppercase',
              textDecoration: 'none', transition: 'color 100ms',
            }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent-mid)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
            >{link}</a>
          ))}
        </div>

      </div>
    </footer>
  )
}