import { useAuth } from '@/hooks/useAuth'

export default function DashboardPage() {
  const { logout } = useAuth()

  return (
    <div style={{
      minHeight: '100vh', background: 'var(--bg)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexDirection: 'column', gap: '1rem',
    }}>
      <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 32, fontStyle: 'italic', color: 'var(--text-primary)' }}>
        Welcome to SaveStack
      </h1>
      <p style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
        Your bookmarks are syncing...
      </p>
      <button
        onClick={logout}
        style={{
          fontFamily: 'var(--font-sans)', fontSize: 13,
          color: 'var(--text-muted)', background: 'transparent',
          border: '0.5px solid var(--border-strong)',
          borderRadius: 'var(--radius-md)', padding: '0.5rem 1.25rem',
          cursor: 'pointer', marginTop: '1rem',
        }}>
        Sign out
      </button>
    </div>
  )
}