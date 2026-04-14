import { Search, Bookmark, BookmarkCheck, Folder, Tag } from 'lucide-react'
import { Wordmark } from '@/components/common/Wordmark'

const sampleBookmarks = [
  {
    initials: 'DP',
    color: '#10B981',
    name: 'Design Philosophy',
    handle: '@design_phil',
    time: '2h',
    text: "Great design isn't about complexity. It's about removing everything that doesn't need to be there until you are left with the purest form of the intent.",
    tags: ['design', 'philosophy'],
  },
  {
    initials: 'TI',
    color: '#6366F1',
    name: 'Technologist',
    handle: '@tech_insider',
    time: '5h',
    text: 'Thread: How the new AI infrastructure models are reshaping the edge computing landscape. A deep dive into why this matters for every dev team. 1/12 🧵',
    tags: ['thread', 'AI'],
  },
  {
    initials: 'SA',
    color: '#F59E0B',
    name: 'Startup Atlas',
    handle: '@startup_atlas',
    time: '1d',
    text: 'The best founders I know obsess over one thing: making the next 10 minutes of the user\'s experience as good as possible. Not the vision. The next 10 minutes.',
    tags: ['startups'],
  },
]

const sidebarItems = [
  { icon: Bookmark, label: 'All Bookmarks', active: true, count: '248' },
  { icon: BookmarkCheck, label: 'Unread', active: false, count: '12' },
  { icon: Folder, label: 'Folders', active: false },
  { icon: Tag, label: 'Tags', active: false },
]

export default function AppMockup() {
  return (
    <section className="px-4 pb-24 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        {/* Browser chrome */}
        <div className="overflow-hidden rounded-2xl border border-border-strong shadow-2xl shadow-black/60">
          {/* Chrome bar */}
          <div className="flex items-center gap-3 border-b border-border-subtle bg-bg-subtle px-4 py-3">
            <div className="flex gap-1.5">
              <div className="h-3 w-3 rounded-full bg-[#FF5F57]" />
              <div className="h-3 w-3 rounded-full bg-[#FEBC2E]" />
              <div className="h-3 w-3 rounded-full bg-[#28C840]" />
            </div>
            <div className="mx-2 flex h-6 flex-1 max-w-xs items-center rounded-md border border-border-subtle bg-bg px-3">
              <span className="text-xs text-text-muted">app.savestack.io/bookmarks</span>
            </div>
          </div>

          {/* App shell */}
          <div className="flex h-[360px] bg-bg md:h-[520px]">
            {/* Sidebar — hidden on small screens */}
            <aside className="hidden w-52 shrink-0 flex-col border-r border-border-subtle md:flex">
              {/* Logo */}
              <div className="border-b border-border-subtle px-4 py-3">
                <Wordmark />
              </div>

              {/* User */}
              <div className="flex items-center gap-2.5 border-b border-border-subtle px-4 py-3">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-light text-[10px] font-semibold text-brand-mid">
                  AR
                </div>
                <div className="min-w-0">
                  <div className="truncate text-xs font-medium text-text-primary">@archivist</div>
                  <div className="text-[10px] text-text-muted">Archivist</div>
                </div>
              </div>

              {/* Nav */}
              <nav className="flex flex-col gap-0.5 p-2">
                {sidebarItems.map(({ icon: Icon, label, active, count }) => (
                  <div
                    key={label}
                    className={`flex items-center gap-2 rounded-md px-2 py-1.5 text-xs ${
                      active
                        ? 'bg-brand-light font-medium text-brand-mid'
                        : 'text-text-secondary'
                    }`}
                  >
                    <Icon size={13} />
                    <span className="flex-1">{label}</span>
                    {count && (
                      <span className={`${active ? 'text-brand-mid' : 'text-text-muted'}`}>
                        {count}
                      </span>
                    )}
                  </div>
                ))}
              </nav>
            </aside>

            {/* Main content */}
            <div className="flex min-w-0 flex-1 flex-col">
              {/* Toolbar */}
              <div className="flex items-center gap-2 border-b border-border-subtle px-4 py-3">
                <div className="flex flex-1 items-center gap-2 rounded-lg border border-border-subtle bg-bg-subtle px-3 py-1.5">
                  <Search size={13} className="shrink-0 text-text-muted" />
                  <span className="text-xs text-text-muted">Search bookmarks...</span>
                </div>
                <div className="hidden items-center gap-1 sm:flex">
                  <div className="rounded-md border border-border-subtle px-2.5 py-1 text-xs text-text-muted">
                    Sort ↓
                  </div>
                  <div className="rounded-md border border-border-subtle px-2.5 py-1 text-xs text-text-muted">
                    Filter
                  </div>
                </div>
              </div>

              {/* Bookmark feed */}
              <div className="flex-1 overflow-hidden p-3 space-y-2.5">
                {sampleBookmarks.map((bm) => (
                  <div
                    key={bm.handle}
                    className="rounded-xl border border-border-subtle bg-bg-card p-3.5"
                  >
                    {/* Author row */}
                    <div className="mb-2 flex items-center gap-2">
                      <div
                        className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[9px] font-semibold text-white"
                        style={{ background: bm.color }}
                      >
                        {bm.initials}
                      </div>
                      <span className="text-[11px] font-medium text-text-primary">{bm.name}</span>
                      <span className="text-[10px] text-text-muted">{bm.handle}</span>
                      <span className="ml-auto text-[10px] text-text-muted">{bm.time}</span>
                    </div>

                    {/* Text */}
                    <p className="line-clamp-2 text-[11px] leading-relaxed text-text-secondary">
                      {bm.text}
                    </p>

                    {/* Tags */}
                    <div className="mt-2 flex gap-1.5">
                      {bm.tags.map(tag => (
                        <span
                          key={tag}
                          className="rounded-full bg-brand-light px-2 py-0.5 text-[9px] font-medium text-brand-mid"
                        >
                          #{tag}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
