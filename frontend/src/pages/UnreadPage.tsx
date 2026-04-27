import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { SidebarTrigger } from '@/components/ui/sidebar'
import BookmarkFeed from '@/components/bookmarks/BookmarkFeed'
import { Button } from '@/components/ui/button'
import {
  useUnreadBookmarks,
  useDeleteBookmark,
  useMarkAsRead,
  useFolders,
  useTags,
  useAddBookmarkToFolder,
  useRemoveBookmarkFromFolder,
  useAddTagToBookmark,
  useRemoveTagFromBookmark,
} from '@/features/bookmarks/hooks'

export default function UnreadPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const page = Number(searchParams.get('page')) || 0
  const { data, isLoading, isError, isFetching } = useUnreadBookmarks(page)
  const { data: foldersData } = useFolders()
  const { data: tagsData } = useTags()
  const deleteMutation = useDeleteBookmark()
  const markAsReadMutation = useMarkAsRead()
  const addToFolderMutation = useAddBookmarkToFolder()
  const removeFromFolderMutation = useRemoveBookmarkFromFolder()
  const addTagMutation = useAddTagToBookmark()
  const removeTagMutation = useRemoveTagFromBookmark()

  async function handleDelete(id: string) {
    setDeletingId(id)
    try {
      await deleteMutation.mutateAsync(id)
    } finally {
      setDeletingId(null)
    }
  }

  async function handleToggleRead(id: string, isRead: boolean) {
    await markAsReadMutation.mutateAsync({ bookmarkId: id, isRead })
  }

  async function handleAddToFolder(bookmarkId: string, folderId: string) {
    await addToFolderMutation.mutateAsync({ bookmarkId, folderId })
  }

  async function handleRemoveFromFolder(bookmarkId: string, folderId: string) {
    await removeFromFolderMutation.mutateAsync({ bookmarkId, folderId })
  }

  async function handleAddTag(bookmarkId: string, tagId: string) {
    await addTagMutation.mutateAsync({ bookmarkId, tagId })
  }

  async function handleRemoveTag(bookmarkId: string, tagId: string) {
    await removeTagMutation.mutateAsync({ bookmarkId, tagId })
  }

  const hasMore = data?.pagination.hasMore ?? false

  return (
    <div className="flex h-full flex-col">
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border-subtle px-4 sm:px-6">
        <SidebarTrigger className="text-text-muted hover:text-text-primary" />
        <h1 className="font-serif italic text-lg text-text-primary">Unread</h1>
        {data && data.data.length > 0 && (
          <span className="ml-1 rounded-full bg-brand-light px-2 py-0.5 text-xs font-medium text-brand-mid">
            {data.pagination.total}
          </span>
        )}
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
        <BookmarkFeed
          bookmarks={data?.data}
          isLoading={isLoading}
          isError={isError}
          onDelete={handleDelete}
          onToggleRead={handleToggleRead}
          onAddToFolder={handleAddToFolder}
          onRemoveFromFolder={handleRemoveFromFolder}
          onAddTag={handleAddTag}
          onRemoveTag={handleRemoveTag}
          availableFolders={foldersData}
          availableTags={tagsData}
          deletingId={deletingId}
          emptyMessage="You're all caught up"
          emptyDescription="New bookmarks synced from X will appear here."
        />

        {hasMore && (
          <div className="mt-6 flex justify-center">
            <Button
              variant="outline"
              onClick={() => setSearchParams((prev) => { prev.set('page', String(page + 1)); return prev })}
              disabled={isFetching}
              className="border-border-subtle bg-bg-subtle text-text-secondary hover:text-text-primary"
            >
              {isFetching ? 'Loading...' : 'Load more'}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
