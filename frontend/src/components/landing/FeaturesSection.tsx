import { RefreshCw, Search, FolderOpen, BookmarkCheck, type LucideIcon } from 'lucide-react'

const features: { icon: LucideIcon; title: string; desc: string }[] = [
  {
    icon: RefreshCw,
    title: 'Auto-sync',
    desc: 'Your bookmarks sync every few minutes from X. Fully automatic — no imports, no manual steps.',
  },
  {
    icon: Search,
    title: 'Full-text search',
    desc: "Search inside every post you've saved \u2014 text, links, handles, thread context. Everything.",
  },
  {
    icon: FolderOpen,
    title: 'Smart folders',
    desc: 'Create folders and drag bookmarks into them. Organize exactly how your brain works.',
  },
  {
    icon: BookmarkCheck,
    title: 'Unread queue',
    desc: "Know what's new since your last visit. Badge indicator keeps you up to date at a glance.",
  },
]

export default function FeaturesSection() {
  return (
    <section id="features" className="bg-bg-subtle px-4 py-24 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        {/* Heading */}
        <div className="mb-12">
          <h2 className="font-serif italic text-4xl text-text-primary md:text-5xl">
            Everything you need to{' '}
            <span className="text-brand-mid">tame your bookmarks.</span>
          </h2>
          <p className="mt-4 max-w-md text-text-secondary">
            Simple, powerful, and built around how X power users actually think and work.
          </p>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {features.map(({ icon: Icon, title, desc }) => (
            <div
              key={title}
              className="group flex flex-col gap-4 rounded-xl border border-border-subtle bg-bg-card p-6 transition-colors hover:border-border-strong"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-light text-brand-mid">
                <Icon size={18} />
              </div>
              <div>
                <h3 className="mb-1.5 text-sm font-semibold text-text-primary">{title}</h3>
                <p className="text-sm leading-relaxed text-text-secondary">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
