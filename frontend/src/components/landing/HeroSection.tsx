import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { ArrowDown } from 'lucide-react'

function XLogo() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  )
}

export default function HeroSection() {
  const { loginWithX } = useAuth()

  return (
    <section className="flex flex-col items-center justify-center px-4 py-24 text-center sm:px-6 lg:px-8 lg:py-32">
      {/* Badge */}
      <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-brand/20 bg-brand-light px-3 py-1.5">
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-brand-mid" />
        <span className="text-label text-brand-mid">Now syncing your X bookmarks</span>
      </div>

      {/* Headline */}
      <h1 className="text-display mb-6 max-w-4xl text-5xl sm:text-6xl lg:text-7xl">
        <span className="text-text-primary">Your X bookmarks,</span>
        <br />
        <span className="text-brand-mid">finally organized.</span>
      </h1>

      {/* Subtext */}
      <p className="mb-10 max-w-xl text-lg leading-relaxed text-text-secondary">
        Stop losing threads in the void. SaveStack automatically syncs every post
        you've saved and makes them searchable in seconds.
      </p>

      {/* CTAs */}
      <div className="flex flex-col gap-3 sm:flex-row">
        <Button
          onClick={loginWithX}
          size="lg"
          className="h-auto gap-2.5 rounded-xl px-8 py-3.5 text-base"
        >
          <XLogo />
          Connect with X
        </Button>
        <Button
          variant="outline"
          size="lg"
          className="h-auto gap-2 rounded-xl px-8 py-3.5 text-base text-text-secondary"
          onClick={() => {
            document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })
          }}
        >
          See how it works
          <ArrowDown size={16} />
        </Button>
      </div>
    </section>
  )
}
