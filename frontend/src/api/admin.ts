import axios, { AxiosRequestConfig } from 'axios'
import { authStore } from '@/store/auth'

const ADMIN_BASE_URL = import.meta.env.VITE_ADMIN_BASE_URL ?? '/api/admin'

const adminClient = axios.create({
  baseURL: ADMIN_BASE_URL,
})

adminClient.interceptors.request.use(config => {
  const token = authStore.getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

adminClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      authStore.clearTokens()
      window.location.href = '/'
    }
    return Promise.reject(error)
  }
)

export const adminApi = {
  get: <T>(url: string, config?: AxiosRequestConfig) =>
    adminClient.get<T>(url, config).then(res => res.data),
  
  post: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    adminClient.post<T>(url, data, config).then(res => res.data),
  
  put: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    adminClient.put<T>(url, data, config).then(res => res.data),
  
  delete: <T>(url: string, config?: AxiosRequestConfig) =>
    adminClient.delete<T>(url, config).then(res => res.data),
  
  patch: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    adminClient.patch<T>(url, data, config).then(res => res.data),
}

export default adminClient