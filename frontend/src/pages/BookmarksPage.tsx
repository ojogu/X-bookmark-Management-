import { useState } from 'react'
import { SidebarTrigger } from '@/components/ui/sidebar'
import BookmarkFeed from '@/components/bookmarks/BookmarkFeed'
import BookmarkToolbar from '@/components/bookmarks/BookmarkToolbar'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'
import {
  useBookmarks,
  useDeleteBookmark,
  useMarkAsRead,
  useTags,
  useFolders,
  useAddBookmarkToFolder,
  useRemoveBookmarkFromFolder,
  useAddTagToBookmark,
  useRemoveTagFromBookmark,
} from '@/features/bookmarks/hooks'
import { useDebounce } from '@/hooks/useDebounce'
import type { SortOption, FilterState } from '@/types'

export default function BookmarksPage() {
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<SortOption>('date-desc')
  const [filter, setFilter] = useState<FilterState>({ tagIds: [] })
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [page, setPage] = useState(0)

  const debouncedSearch = useDebounce(search, 350)

  const { data, isLoading, isError, isFetching } = useBookmarks({
    search: debouncedSearch,
    sort,
    filter,
    page,
  })
  const { data: tagsData } = useTags()
  const { data: foldersData } = useFolders()
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
      toast.success('Bookmark deleted')
    } catch {
      toast.error('Failed to delete bookmark')
    } finally {
      setDeletingId(null)
    }
  }

  async function handleToggleRead(id: string, isRead: boolean) {
    await markAsReadMutation.mutateAsync({ bookmarkId: id, isRead })
  }

  async function handleAddToFolder(bookmarkId: string, folderId: string) {
    try {
      await addToFolderMutation.mutateAsync({ bookmarkId, folderId })
      toast.success('Added to folder')
    } catch {
      toast.error('Failed to add to folder')
    }
  }

  async function handleRemoveFromFolder(bookmarkId: string, folderId: string) {
    try {
      await removeFromFolderMutation.mutateAsync({ bookmarkId, folderId })
      toast.success('Removed from folder')
    } catch {
      toast.error('Failed to remove from folder')
    }
  }

  async function handleAddTag(bookmarkId: string, tagId: string) {
    await addTagMutation.mutateAsync({ bookmarkId, tagId })
  }

  async function handleRemoveTag(bookmarkId: string, tagId: string) {
    await removeTagMutation.mutateAsync({ bookmarkId, tagId })
  }

  function handleSearchChange(value: string) {
    setSearch(value)
    setPage(0)
  }

  function handleSortChange(value: SortOption) {
    setSort(value)
    setPage(0)
  }

  function handleFilterChange(value: FilterState) {
    setFilter(value)
    setPage(0)
  }

  const hasMore = data?.pagination.hasMore ?? false

  return (
    <div className="flex h-full flex-col">
      {/* Page header */}
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border-subtle px-4 sm:px-6">
        <SidebarTrigger className="text-text-muted hover:text-text-primary" />
        <h1 className="font-serif italic text-lg text-text-primary">All Bookmarks</h1>
      </header>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
        <BookmarkToolbar
          search={search}
          onSearchChange={handleSearchChange}
          sort={sort}
          onSortChange={handleSortChange}
          filter={filter}
          onFilterChange={handleFilterChange}
          availableTags={tagsData}
          totalCount={data?.pagination.total}
        />

        <div className="mt-6">
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
            emptyMessage={search ? 'No results found' : 'No bookmarks yet'}
            emptyDescription={
              search
                ? 'Try a different search term or clear your filters.'
                : 'Connect your X account to start syncing your saved posts.'
            }
          />
        </div>

        {/* Load More button */}
        {hasMore && (
          <div className="mt-6 flex justify-center">
            <Button
              variant="outline"
              onClick={() => setPage((p) => p + 1)}
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
