import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { authStore } from '@/store/auth'
import { useFetchUserInfoFresh, useTriggerSync } from '@/features/bookmarks/hooks'
import { Wordmark } from '@/components/common/Wordmark'

type OnboardingStep = 'connecting' | 'fetching_profile' | 'syncing_bookmarks' | 'done'
type Status = 'onboarding' | 'success' | 'error'

const onboardingMessages: Record<OnboardingStep, string> = {
  connecting: 'Connecting your X account…',
  fetching_profile: 'Getting your profile…',
  syncing_bookmarks: 'Reading your saved posts…',
  done: 'Building your library…',
}

export default function CallbackPage() {
  const navigate = useNavigate()
  const [status, setStatus] = useState<Status>('onboarding')
  const [step, setStep] = useState<OnboardingStep>('connecting')

  const fetchUserInfoFresh = useFetchUserInfoFresh()
  const triggerSync = useTriggerSync()

  useEffect(() => {
    if (authStore.isAuthenticated()) {
      navigate('/dashboard', { replace: true })
      return
    }
  }, [navigate])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const accessToken = params.get('access-token')
    const refreshToken = params.get('refresh-token')
    const error = params.get('error')

    if (error || !accessToken || !refreshToken) {
      setStatus('error')
      return
    }

    authStore.setTokens(accessToken, refreshToken)
    window.history.replaceState({}, '', '/callback')

    runOnboarding()
  }, [navigate])

  const runOnboarding = async () => {
    try {
      setStep('fetching_profile')
      await fetchUserInfoFresh.mutateAsync()

      setStep('syncing_bookmarks')
      await triggerSync.mutateAsync()

      setStep('done')
      setTimeout(() => {
        setStatus('success')
        navigate('/dashboard/profile', { replace: true })
      }, 600)
    } catch {
      setStatus('error')
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 bg-bg px-4">
      <Link to="/">
        <Wordmark />
      </Link>

      {status === 'onboarding' && (
        <div className="flex flex-col items-center gap-6">
          <div className="h-px w-48 overflow-hidden rounded-full bg-border-subtle">
            <div
              className="h-full rounded-full bg-brand"
              style={{ animation: 'callback-bar 1.8s ease-in-out infinite' }}
            />
          </div>

          <p className="text-sm text-text-secondary">{onboardingMessages[step]}</p>

          <p className="max-w-xs text-center text-xs leading-relaxed text-text-muted">
            First-time import may take a moment depending on how many posts you've saved.
          </p>
        </div>
      )}

      {status === 'success' && (
        <div className="flex flex-col items-center gap-6">
          <div className="h-px w-48 overflow-hidden rounded-full bg-border-subtle">
            <div
              className="h-full rounded-full bg-brand"
              style={{ width: '100%' }}
            />
          </div>

          <p className="text-sm text-text-secondary">All done!</p>
        </div>
      )}

      {status === 'error' && (
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
            <span className="text-xl text-destructive">✕</span>
          </div>
          <p className="text-sm text-text-primary">Something went wrong</p>
          <p className="text-xs text-text-muted">Please try connecting your X account again.</p>
          <Button onClick={() => navigate('/')} variant="outline">
            Back to home
          </Button>
        </div>
      )}

      <style>{`
        @keyframes callback-bar {
          0%   { width: 0%;   margin-left: 0; }
          50%  { width: 60%;  margin-left: 20%; }
          100% { width: 0%;   margin-left: 100%; }
        }
      `}</style>
    </div>
  )
}