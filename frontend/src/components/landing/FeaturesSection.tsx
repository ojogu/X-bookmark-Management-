const features = [
  {
    icon: '↻',
    title: 'Auto-sync',
    desc: 'Your bookmarks are automatically imported from X every few minutes. Never lift a finger.',
  },
  {
    icon: '⌕',
    title: 'Full-text search',
    desc: "Search through the content of every post you've ever saved, including links and media captions.",
  },
  {
    icon: '◈',
    title: 'Smart tags',
    desc: 'AI-powered categorization that groups your bookmarks by topic, sentiment, and author automatically.',
  },
  {
    icon: '≡',
    title: 'Thread reconstruction',
    desc: 'View fragmented X threads as beautiful, clean, long-form articles. No more "1/10" clicks.',
  },
]

export default function FeaturesSection() {
  return (
    <section style={{ background: 'var(--bg-subtle)', padding: '6rem 1.5rem' }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>

        <div style={{ marginBottom: '4rem' }}>
          <h2 style={{
            fontFamily: 'var(--font-serif)', fontSize: 'clamp(2rem, 4vw, 3rem)',
            fontWeight: 400, color: 'var(--text-primary)', marginBottom: '1rem',
          }}>
            Built for how X users{' '}
            <em style={{ fontStyle: 'italic', color: 'var(--accent-mid)' }}>actually think</em>.
          </h2>
          <p style={{ fontSize: 16, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            Every feature exists to help you find what you saved, when you need it.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.5rem' }}>
          {features.map(({ icon, title, desc }) => (
            <div key={title} style={{
              background: 'var(--bg-card)', padding: '2rem',
              borderRadius: 'var(--radius-lg)', border: '0.5px solid var(--border)',
              display: 'flex', flexDirection: 'column', gap: '1rem',
              transition: 'border-color 100ms',
            }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--accent-mid)')}
              onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
            >
              <div style={{
                width: 40, height: 40, borderRadius: 'var(--radius-md)',
                background: 'var(--accent-light)', display: 'flex',
                alignItems: 'center', justifyContent: 'center',
                fontSize: 18, color: 'var(--accent-mid)',
              }}>{icon}</div>
              <div style={{ fontSize: 15, fontWeight: 500, color: 'var(--text-primary)' }}>{title}</div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{desc}</div>
            </div>
          ))}
        </div>

      </div>
    </section>
  )
}