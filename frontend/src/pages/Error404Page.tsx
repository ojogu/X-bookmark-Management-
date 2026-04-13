import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { ArrowLeft } from 'lucide-react'

export default function Error404Page() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 bg-bg px-4 text-center">
      <Link to="/" className="font-serif italic text-xl text-text-primary">
        Save<span className="text-brand-mid">Stack</span>
      </Link>

      <div className="flex flex-col items-center gap-4">
        <p className="text-label text-text-muted">Error</p>
        <h1 className="text-display text-8xl text-text-primary sm:text-9xl">404</h1>
        <p className="mt-2 max-w-sm text-text-secondary">
          This page doesn't exist. It may have been moved, or the URL might be wrong.
        </p>
      </div>

      <Button asChild variant="outline" className="gap-2">
        <Link to="/">
          <ArrowLeft size={14} />
          Back to home
        </Link>
      </Button>
    </div>
  )
}
