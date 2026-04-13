import { BookmarkX } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import BookmarkCard from './BookmarkCard'
import type { Bookmark, Folder as FolderType, Tag as TagType } from '@/types'

interface BookmarkFeedProps {
  bookmarks: Bookmark[] | undefined
  isLoading: boolean
  isError: boolean
  onDelete: (id: string) => void
  onToggleRead?: (id: string, isRead: boolean) => void
  onAddToFolder?: (bookmarkId: string, folderId: string) => void
  onRemoveFromFolder?: (bookmarkId: string, folderId: string) => void
  onAddTag?: (bookmarkId: string, tagId: string) => void
  onRemoveTag?: (bookmarkId: string, tagId: string) => void
  availableFolders?: FolderType[]
  availableTags?: TagType[]
  bookmarkFoldersMap?: Record<string, string[]>
  deletingId?: string | null
  emptyMessage?: string
  emptyDescription?: string
}

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-border-subtle bg-bg-card p-4">
      <div className="mb-3 flex items-center gap-2">
        <Skeleton className="h-6 w-6 rounded-full" />
        <Skeleton className="h-3.5 w-28 rounded" />
        <Skeleton className="h-3 w-20 rounded" />
        <Skeleton className="ml-auto h-3 w-10 rounded" />
      </div>
      <Skeleton className="mb-1.5 h-3.5 w-full rounded" />
      <Skeleton className="mb-1.5 h-3.5 w-5/6 rounded" />
      <Skeleton className="h-3.5 w-3/4 rounded" />
      <div className="mt-3 flex gap-1.5">
        <Skeleton className="h-5 w-14 rounded-full" />
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
    </div>
  )
}

export default function BookmarkFeed({
  bookmarks,
  isLoading,
  isError,
  onDelete,
  onToggleRead,
  onAddToFolder,
  onRemoveFromFolder,
  onAddTag,
  onRemoveTag,
  availableFolders = [],
  availableTags = [],
  bookmarkFoldersMap = {},
  deletingId,
  emptyMessage = 'No bookmarks found',
  emptyDescription = 'Try adjusting your search or filters.',
}: BookmarkFeedProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col gap-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10">
          <BookmarkX size={24} className="text-destructive" />
        </div>
        <p className="text-sm font-medium text-text-primary">Something went wrong</p>
        <p className="mt-1 text-xs text-text-muted">Failed to load bookmarks. Please try again.</p>
      </div>
    )
  }

  if (!bookmarks || bookmarks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-bg-subtle">
          <BookmarkX size={24} className="text-text-muted" />
        </div>
        <p className="text-sm font-medium text-text-primary">{emptyMessage}</p>
        <p className="mt-1 text-xs text-text-muted">{emptyDescription}</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {bookmarks.map((bookmark) => (
        <BookmarkCard
          key={bookmark.id}
          bookmark={bookmark}
          onDelete={onDelete}
          onToggleRead={onToggleRead}
          onAddToFolder={onAddToFolder}
          onRemoveFromFolder={onRemoveFromFolder}
          onAddTag={onAddTag}
          onRemoveTag={onRemoveTag}
          availableFolders={availableFolders}
          availableTags={availableTags}
          bookmarkFolders={bookmarkFoldersMap[bookmark.id] || []}
          isDeleting={deletingId === bookmark.id}
        />
      ))}
    </div>
  )
}
