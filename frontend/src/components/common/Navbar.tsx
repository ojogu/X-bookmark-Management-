import { Link } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetTitle,
} from '@/components/ui/sheet'
import { useAuth } from '@/hooks/useAuth'

const navLinks = ['Features', 'Pricing', 'Blog']

function XLogo({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  )
}

export default function Navbar() {
  const { loginWithX } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border-subtle bg-bg/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <Link to="/" className="font-serif italic text-xl text-text-primary">
          Save<span className="text-brand-mid">Stack</span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden items-center gap-8 md:flex">
          {navLinks.map(link => (
            <a
              key={link}
              href="#"
              className="text-sm font-medium text-text-secondary transition-colors hover:text-text-primary"
            >
              {link}
            </a>
          ))}
        </nav>

        {/* Desktop CTA */}
        <div className="hidden items-center gap-2 md:flex">
          <Button variant="ghost" onClick={loginWithX} className="text-sm">
            Sign in
          </Button>
          <Button onClick={loginWithX} className="gap-2 text-sm">
            <XLogo />
            Get started
          </Button>
        </div>

        {/* Mobile hamburger */}
        <button
          className="flex h-9 w-9 items-center justify-center rounded-lg text-text-secondary transition-colors hover:text-text-primary md:hidden"
          onClick={() => setMobileOpen(true)}
          aria-label="Open menu"
        >
          <Menu size={20} />
        </button>
      </div>

      {/* Mobile Sheet */}
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="right" className="w-72 border-l border-border-subtle bg-bg-subtle p-0">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <div className="flex h-full flex-col">
            {/* Sheet header */}
            <div className="flex items-center justify-between border-b border-border-subtle px-6 py-5">
              <span className="font-serif italic text-xl text-text-primary">
                Save<span className="text-brand-mid">Stack</span>
              </span>
              <button
                onClick={() => setMobileOpen(false)}
                className="flex h-8 w-8 items-center justify-center rounded-md text-text-muted hover:text-text-primary"
              >
                <X size={18} />
              </button>
            </div>

            {/* Links */}
            <nav className="flex flex-col gap-1 p-4">
              {navLinks.map(link => (
                <a
                  key={link}
                  href="#"
                  onClick={() => setMobileOpen(false)}
                  className="rounded-lg px-3 py-2.5 text-sm font-medium text-text-secondary transition-colors hover:bg-bg-card hover:text-text-primary"
                >
                  {link}
                </a>
              ))}
            </nav>

            {/* CTAs */}
            <div className="mt-auto flex flex-col gap-2 border-t border-border-subtle p-4">
              <Button variant="outline" onClick={loginWithX} className="w-full">
                Sign in
              </Button>
              <Button onClick={loginWithX} className="w-full gap-2">
                <XLogo />
                Get started
              </Button>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </header>
  )
}
