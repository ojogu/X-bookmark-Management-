import { useEffect, useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import client from '@/api/client'

interface UserInfo {
  id: string
  username: string
  name: string
  profile_image_url: string | null
  description: string | null
  followers_count: number
  following_count: number
  tweet_count: number
  verified: boolean
  location: string | null
}

export default function DashboardPage() {
  const { logout } = useAuth()
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    client.get<UserInfo>('/X/user-info/fresh')
      .then(res => setUserInfo(res.data))
      .catch(err => setError(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div style={{
      minHeight: '100vh', background: 'var(--bg)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexDirection: 'column', gap: '1.5rem',
    }}>
      <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 32, fontStyle: 'italic', color: 'var(--text-primary)' }}>
        Welcome to SaveStack
      </h1>

      {loading && (
        <p style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
          Loading user info...
        </p>
      )}

      {error && (
        <p style={{ fontSize: 14, color: '#E24B4A' }}>
          Error: {error}
        </p>
      )}

      {userInfo && !loading && !error && (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          gap: '1rem', padding: '1.5rem',
          background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border)', maxWidth: 400,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            {userInfo.profile_image_url ? (
              <img
                src={userInfo.profile_image_url}
                alt={userInfo.username}
                style={{
                  width: 60, height: 60, borderRadius: '50%',
                  objectFit: 'cover',
                }}
              />
            ) : (
              <div style={{
                width: 60, height: 60, borderRadius: '50%',
                background: 'var(--border)',
              }} />
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{
                  fontFamily: 'var(--font-sans)', fontSize: 18, fontWeight: 600,
                  color: 'var(--text-primary)',
                }}>
                  {userInfo.name}
                </span>
                {userInfo.verified && (
                  <span style={{ color: 'var(--accent)' }}>✓</span>
                )}
              </div>
              <span style={{
                fontFamily: 'var(--font-sans)', fontSize: 14,
                color: 'var(--text-secondary)',
              }}>
                @{userInfo.username}
              </span>
            </div>
          </div>

          {userInfo.description && (
            <p style={{
              fontFamily: 'var(--font-sans)', fontSize: 14,
              color: 'var(--text-secondary)', textAlign: 'center',
              maxWidth: 320, lineHeight: 1.5,
            }}>
              {userInfo.description}
            </p>
          )}

          <div style={{
            display: 'flex', gap: '1.5rem',
            fontFamily: 'var(--font-sans)', fontSize: 13,
          }}>
            <div style={{ textAlign: 'center' }}>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                {userInfo.followers_count.toLocaleString()}
              </span>
              <span style={{ color: 'var(--text-muted)' }}> followers</span>
            </div>
            <div style={{ textAlign: 'center' }}>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                {userInfo.following_count.toLocaleString()}
              </span>
              <span style={{ color: 'var(--text-muted)' }}> following</span>
            </div>
            <div style={{ textAlign: 'center' }}>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                {userInfo.tweet_count.toLocaleString()}
              </span>
              <span style={{ color: 'var(--text-muted)' }}> posts</span>
            </div>
          </div>

          {userInfo.location && (
            <span style={{
              fontFamily: 'var(--font-sans)', fontSize: 12,
              color: 'var(--text-muted)',
            }}>
              📍 {userInfo.location}
            </span>
          )}
        </div>
      )}

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