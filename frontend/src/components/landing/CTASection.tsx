import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'

function XLogo() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  )
}

export default function CTASection() {
  const { loginWithX } = useAuth()

  return (
    <section className="bg-bg-subtle px-4 py-24 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-3xl">
        <div className="relative overflow-hidden rounded-2xl border border-border-strong bg-bg-card px-8 py-16 text-center">
          {/* Subtle glow */}
          <div
            className="pointer-events-none absolute inset-0 opacity-30"
            style={{
              background: 'radial-gradient(ellipse 80% 50% at 50% 0%, rgba(16,185,129,0.15) 0%, transparent 70%)',
            }}
          />

          <p className="text-label relative z-10 mb-4 text-text-muted">Get started — it's free</p>
          <h2 className="font-serif italic relative z-10 mb-4 text-4xl text-text-primary lg:text-5xl">
            Take back your bookmarks.
          </h2>
          <p className="relative z-10 mb-10 text-text-secondary leading-relaxed max-w-md mx-auto">
            Stop losing posts you meant to read. Connect your X account and your library is ready in under a minute.
          </p>

          <Button
            onClick={loginWithX}
            size="lg"
            className="relative z-10 h-auto gap-2.5 rounded-xl px-10 py-3.5 text-base"
          >
            <XLogo />
            Connect with X
          </Button>
        </div>
      </div>
    </section>
  )
}
