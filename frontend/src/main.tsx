import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import './index.css'
import App from './App.tsx'

function getSystemTheme() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function getStoredTheme() {
  const stored = localStorage.getItem('savestack-theme')
  if (stored === 'light' || stored === 'dark' || stored === 'system') return stored
  return null
}

function resolveTheme() {
  const theme = getStoredTheme()
  return theme === 'system' || !theme ? getSystemTheme() : theme
}

function updateFavicon(isDark: boolean) {
  const favicon = document.querySelector('link[rel="icon"]') as HTMLLinkElement
  if (favicon) {
    favicon.href = isDark ? '/favicon-dark.svg' : '/favicon-light.svg'
  }
}

const theme = resolveTheme()
const isDark = theme === 'dark'
document.documentElement.classList.toggle('dark', isDark)
updateFavicon(isDark)

const observer = new MutationObserver((mutations) => {
  mutations.forEach((mutation) => {
    if (mutation.attributeName === 'class') {
      const hasDark = document.documentElement.classList.contains('dark')
      updateFavicon(hasDark)
    }
  })
})
observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10 * 1000,
      refetchOnWindowFocus: true,
      retry: 1,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <Toaster 
        position="top-center" 
        richColors 
        duration={3000}
        theme={isDark ? 'dark' : 'light'}
        toastOptions={{
          style: {
            borderRadius: '8px',
          },
        }}
      />
    </QueryClientProvider>
  </StrictMode>,
)
