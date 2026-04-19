const REFRESH_TOKEN_KEY = 'savestack_refresh_token'

// Access token lives in memory only — lost on refresh, restored via refresh token
let inMemoryAccessToken: string | null = null

export const authStore = {
  getAccessToken(): string | null {
    return inMemoryAccessToken
  },

  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY)
  },

  //TODO: refresh token should be stored in an httpOnly cookie set by the backend.
// localStorage is readable by JavaScript and vulnerable to XSS.
// This requires backend changes: set cookie on /auth/callback redirect,
// read cookie on /auth/refresh-token instead of Authorization header.
// Switch before launch.
  setTokens(accessToken: string, refreshToken: string) {
    inMemoryAccessToken = accessToken
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
  },

  setAccessToken(accessToken: string, storage: 'memory' | 'local' = 'memory') {
    inMemoryAccessToken = accessToken
    if (storage === 'local') {
      localStorage.setItem('savestack_admin_token', accessToken)
    }
  },

  getAdminToken(): string | null {
    return inMemoryAccessToken || localStorage.getItem('savestack_admin_token')
  },

  clearTokens() {
    inMemoryAccessToken = null
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  },

  isAuthenticated(): boolean {
    return !!inMemoryAccessToken || !!this.getRefreshToken()
  },
}