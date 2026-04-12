import axios from 'axios'
import { authStore } from '@/store/auth'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

const client = axios.create({
  baseURL: BASE_URL,
})

// Attach access token to every request
client.interceptors.request.use(config => {
  const token = authStore.getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// On 401 — try to refresh, then retry the original request
let isRefreshing = false
let failedQueue: Array<{
  resolve: (token: string) => void
  reject: (err: unknown) => void
}> = []

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (token) resolve(token)
    else reject(error)
  })
  failedQueue = []
}

client.interceptors.response.use(
  response => response,
  async error => {
    const original = error.config

    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error)
    }

    const refreshToken = authStore.getRefreshToken()
    if (!refreshToken) {
      authStore.clearTokens()
      window.location.href = '/'
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject })
      }).then(token => {
        original.headers.Authorization = `Bearer ${token}`
        return client(original)
      })
    }

    original._retry = true
    isRefreshing = true

    try {
      const response = await axios.get(`${BASE_URL}/auth/refresh-token`, {
        headers: { Authorization: `Bearer ${refreshToken}` },
      })

      const { access_token, refresh_token } = response.data.data
      authStore.setTokens(access_token, refresh_token)
      processQueue(null, access_token)

      original.headers.Authorization = `Bearer ${access_token}`
      return client(original)
    } catch (err) {
      processQueue(err, null)
      authStore.clearTokens()
      window.location.href = '/'
      return Promise.reject(err)
    } finally {
      isRefreshing = false
    }
  }
)

export default client