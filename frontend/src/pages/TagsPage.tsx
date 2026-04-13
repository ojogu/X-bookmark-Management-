import { useState } from 'react'
import { Tag, Plus, Trash2, X } from 'lucide-react'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { useTags, useCreateTag, useDeleteTag } from '@/features/bookmarks/hooks'
import type { Tag as TagType } from '@/types'

export default function TagsPage() {
  const [isCreating, setIsCreating] = useState(false)
  const [newTagName, setNewTagName] = useState('')
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const { data: tags, isLoading, isError } = useTags()
  const createTag = useCreateTag()
  const deleteTag = useDeleteTag()

  async function handleCreateTag() {
    if (!newTagName.trim()) return
    try {
      await createTag.mutateAsync({ name: newTagName.trim() })
      setNewTagName('')
      setIsCreating(false)
    } catch (e) {
      // Error handling
    }
  }

  async function handleDeleteTag(id: string) {
    setDeletingId(id)
    try {
      await deleteTag.mutateAsync(id)
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
              <div
                key={tag.id}
                className={`group flex items-center gap-1.5 rounded-full border border-border-subtle bg-bg-card px-3 py-1.5 text-sm text-text-secondary transition-colors hover:border-border-strong ${
                  deletingId === tag.id ? 'pointer-events-none opacity-50' : ''
                }`}
              >
                <Tag size={11} />
                <span>#{tag.name}</span>
                <span className="text-xs text-text-muted">{tag.bookmarkCount}</span>
                {tag.source === 'user' && (
                  <button
                    onClick={() => handleDeleteTag(tag.id)}
                    className="ml-1 flex h-4 w-4 items-center justify-center rounded text-text-muted opacity-0 transition-all hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                    title="Delete tag"
                  >
                    <Trash2 size={10} />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
