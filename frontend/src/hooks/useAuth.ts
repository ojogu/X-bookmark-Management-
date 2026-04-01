import { useNavigate } from 'react-router-dom'
import { authStore } from '@/store/auth'
import client from '@/api/client'

export function useAuth() {
  const navigate = useNavigate()

    async function loginWithX() {
    try {
        console.log('BASE URL:', import.meta.env.VITE_API_BASE_URL)
        const response = await client.get('/auth/login')
        const { url } = response.data
        window.location.href = url
    } catch (err) {
        console.error('Login error:', err)
        throw new Error('Failed to initiate X login')
    }
    }

  function logout() {
    authStore.clearTokens()
    navigate('/auth')
  }

  function isAuthenticated() {
    return authStore.isAuthenticated()
  }

  return { loginWithX, logout, isAuthenticated }
}