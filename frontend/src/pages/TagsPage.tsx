import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Tag, Plus, Trash2, X } from 'lucide-react'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { toast } from 'sonner'
import { useTags, useCreateTag, useDeleteTag } from '@/features/bookmarks/hooks'
import type { Tag as TagType } from '@/types'

const TAG_COLORS = [
  '#ef4444', '#f97316', '#eab308', '#22c55e',
  '#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899', '#6b7280',
]

export default function TagsPage() {
  const [isCreating, setIsCreating] = useState(false)
  const [newTagName, setNewTagName] = useState('')
  const [newTagColor, setNewTagColor] = useState(TAG_COLORS[5])
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const { data: tags, isLoading, isError } = useTags()
  const createTag = useCreateTag()
  const deleteTag = useDeleteTag()

  async function handleCreateTag() {
    if (!newTagName.trim()) return
    try {
      await createTag.mutateAsync({ name: newTagName.trim(), color: newTagColor })
      setNewTagName('')
      setNewTagColor(TAG_COLORS[5])
      setIsCreating(false)
      toast.success('Tag created')
    } catch {
      toast.error('Failed to create tag')
    }
  }

  async function handleDeleteTag(id: string) {
    setDeletingId(id)
    try {
      await deleteTag.mutateAsync(id)
      toast.success('Tag deleted')
    } catch {
      toast.error('Failed to delete tag')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border-subtle px-4 sm:px-6">
        <SidebarTrigger className="text-text-muted hover:text-text-primary" />
        <h1 className="font-serif italic text-lg text-text-primary">Tags</h1>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
        {/* Create tag section */}
        <div className="mb-6">
          {isCreating ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Input
                  value={newTagName}
                  onChange={(e) => setNewTagName(e.target.value)}
                  placeholder="Tag name"
                  className="h-9 max-w-xs border-border-subtle bg-bg-subtle"
                  onKeyDown={(e) => e.key === 'Enter' && handleCreateTag()}
                  autoFocus
                />
                <Button
                  size="sm"
                  onClick={handleCreateTag}
                  disabled={!newTagName.trim() || createTag.isPending}
                >
                  Create
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setIsCreating(false)
                    setNewTagName('')
                  }}
                >
                  <X size={14} />
                </Button>
              </div>
              <div className="flex gap-1.5">
                {TAG_COLORS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setNewTagColor(c)}
                    className={`h-5 w-5 rounded-full transition-transform ${
                      newTagColor === c ? 'scale-125 ring-2 ring-offset-1 ring-black dark:ring-white' : 'hover:scale-110'
                    }`}
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
            </div>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsCreating(true)}
              className="border-border-subtle bg-bg-subtle text-text-secondary"
            >
              <Plus size={14} className="mr-1.5" />
              New tag
            </Button>
          )}
        </div>

        {isLoading && (
          <div className="flex flex-wrap gap-2">
            {Array.from({ length: 12 }).map((_, i) => (
              <Skeleton key={i} className="h-8 rounded-full" style={{ width: `${60 + Math.random() * 60}px` }} />
            ))}
          </div>
        )}

        {isError && (
          <p className="text-sm text-text-muted">Failed to load tags.</p>
        )}

        {!isLoading && tags && tags.length === 0 && (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-bg-subtle">
              <Tag size={24} className="text-text-muted" />
            </div>
            <p className="text-sm font-medium text-text-primary">No tags yet</p>
            <p className="mt-1 text-xs text-text-muted">
              Create tags to organize your bookmarks.
            </p>
          </div>
        )}

        {tags && tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {tags.map((tag: TagType) => (
              <Link
                key={tag.id}
                to={`/dashboard/tags/${tag.name}`}
                className={`group flex items-center gap-1.5 rounded-full border border-border-subtle bg-bg-card px-3 py-1.5 text-sm text-text-secondary transition-colors hover:border-border-strong ${
                  deletingId === tag.id ? 'pointer-events-none opacity-50' : ''
                }`}
              >
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: tag.color || '#6b7280' }}
                />
                <span>#{tag.name}</span>
                <span className="text-xs text-text-muted">{tag.bookmarkCount}</span>
                {tag.source === 'user' && (
                  <button
                    onClick={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      handleDeleteTag(tag.id)
                    }}
                    className="ml-1 flex h-4 w-4 items-center justify-center rounded text-text-muted opacity-0 transition-all hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                    title="Delete tag"
                  >
                    <Trash2 size={10} />
                  </button>
                )}
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
