const bookmarks = [
  {
    name: 'Design Philosophy',
    handle: '@design_phil',
    time: '2h',
    text: "Great design isn't about complexity. It's about removing everything that doesn't need to be there until you are left with the purest form of the intent.",
    tags: ['DESIGN', 'PHILOSOPHY'],
    initials: 'DP',
    color: '#1D9E75',
  },
  {
    name: 'Technologist',
    handle: '@tech_insider',
    time: '5h',
    text: 'Thread: How the new AI infrastructure models are reshaping the edge computing landscape. 1/12 🧵',
    tags: ['THREAD', 'AI'],
    initials: 'TI',
    color: '#185FA5',
  },
]

export default function AppMockup() {
  return (
    <section style={{ maxWidth: 1280, margin: '0 auto', padding: '0 1.5rem 8rem' }}>
      <div style={{
        background: 'var(--bg-subtle)', borderRadius: 'var(--radius-xl)',
        border: '0.5px solid var(--border)', padding: '4px', overflow: 'hidden',
      }}>
        <div style={{
          background: 'var(--bg-card)', borderRadius: 14,
          border: '0.5px solid var(--border)',
          display: 'flex', height: 580, overflow: 'hidden',
        }}>

          {/* Sidebar */}
          <aside style={{
            width: 240, flexShrink: 0,
            background: 'var(--bg-subtle)',
            borderRight: '0.5px solid var(--border)',
            padding: '1.5rem', display: 'flex',
            flexDirection: 'column', justifyContent: 'space-between',
          }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{
                  width: 32, height: 32, borderRadius: '50%',
                  background: 'var(--accent-light)', display: 'flex',
                  alignItems: 'center', justifyContent: 'center',
                  fontSize: 11, fontWeight: 500, color: 'var(--accent-mid)',
                }}>AR</div>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)' }}>@archivist</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Archivist</div>
                </div>
              </div>

              <nav style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {[
                  { label: 'Library', active: true },
                  { label: 'Folders', active: false },
                  { label: 'New Folder', active: false },
                ].map(({ label, active }) => (
                  <a key={label} href="#" style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '0.5rem 0.75rem', borderRadius: 'var(--radius-sm)',
                    fontSize: 13, fontWeight: active ? 500 : 400,
                    color: active ? 'var(--accent-mid)' : 'var(--text-secondary)',
                    background: active ? 'var(--accent-light)' : 'transparent',
                    textDecoration: 'none',
                  }}>{label}</a>
                ))}
              </nav>
            </div>

            <div style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
              248 Posts Saved
            </div>
          </aside>

          {/* Main content */}
          <div style={{ flex: 1, overflowY: 'auto', background: 'var(--bg-card)' }}>
            <div style={{
              padding: '1.5rem 2rem', borderBottom: '0.5px solid var(--border)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: 22, fontStyle: 'italic', color: 'var(--text-primary)', fontWeight: 400 }}>
                Library
              </h2>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 16, color: 'var(--text-muted)' }}>🔍</span>
                <input placeholder="Search archives..." style={{
                  background: 'transparent', border: 'none', outline: 'none',
                  fontSize: 13, color: 'var(--text-primary)',
                  fontFamily: 'var(--font-sans)',
                }} />
              </div>
            </div>

            <div style={{ padding: '2rem 2rem 2rem 3.5rem', display: 'flex', flexDirection: 'column', gap: '2.5rem' }}>
              {bookmarks.map(({ name, handle, time, text, tags, initials, color }) => (
                <article key={handle} style={{ maxWidth: 560, position: 'relative' }}>
                  <div style={{
                    position: 'absolute', left: -36, top: 0,
                    width: 28, height: 28, borderRadius: '50%',
                    background: color, display: 'flex', alignItems: 'center',
                    justifyContent: 'center', fontSize: 10, fontWeight: 500, color: '#fff',
                  }}>{initials}</div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{name}</span>
                      <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{handle} · {time}</span>
                    </div>
                    <p style={{ fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.6, margin: 0 }}>{text}</p>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {tags.map(tag => (
                        <span key={tag} style={{
                          padding: '3px 10px', borderRadius: 'var(--radius-full)',
                          background: 'var(--accent-light)', color: 'var(--accent-mid)',
                          fontSize: 10, fontWeight: 500, letterSpacing: '0.06em',
                        }}>{tag}</span>
                      ))}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </div>

        </div>
      </div>
    </section>
  )
}