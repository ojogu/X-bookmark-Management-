import { Link } from 'react-router-dom'

const productLinks = ['Features', 'Pricing', 'Blog']
const legalLinks = ['Privacy', 'Terms', 'Support']

export default function Footer() {
  return (
    <footer className="border-t border-border-subtle">
      <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-10 md:flex-row md:justify-between">
          {/* Brand */}
          <div>
            <Link to="/" className="font-serif italic text-xl text-text-primary">
              Save<span className="text-brand-mid">Stack</span>
            </Link>
            <p className="mt-1.5 text-sm text-text-muted">Your bookmarks, organized.</p>
            <p className="mt-6 text-xs text-text-muted">
              © 2026 SaveStack · Built by Ojogu
            </p>
          </div>

          {/* Links */}
          <div className="flex gap-12">
            <div className="flex flex-col gap-3">
              <span className="text-label text-text-muted">Product</span>
              {productLinks.map(l => (
                <a
                  key={l}
                  href="#"
                  className="text-sm text-text-secondary transition-colors hover:text-text-primary"
                >
                  {l}
                </a>
              ))}
            </div>
            <div className="flex flex-col gap-3">
              <span className="text-label text-text-muted">Legal</span>
              {legalLinks.map(l => (
                <a
                  key={l}
                  href="#"
                  className="text-sm text-text-secondary transition-colors hover:text-text-primary"
                >
                  {l}
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>
    </footer>
  )
}
