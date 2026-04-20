import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import { SidebarTrigger } from '@/components/ui/sidebar'
import BookmarkFeed from '@/components/bookmarks/BookmarkFeed'
import BookmarkToolbar from '@/components/bookmarks/BookmarkToolbar'
import { Button } from '@/components/ui/button'
import {
  useFolderBookmarks,
  useDeleteBookmark,
  useMarkAsRead,
  useFolders,
  useTags,
  useAddTagToBookmark,
  useRemoveTagFromBookmark,
  useAddBookmarkToFolder,
  useRemoveBookmarkFromFolder,
} from '@/features/bookmarks/hooks'
import { useDebounce } from '@/hooks/useDebounce'
import type { SortOption, FilterState } from '@/types'

export default function FolderPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<SortOption>('date-desc')
  const [filter, setFilter] = useState<FilterState>({ tagIds: [] })
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [page, setPage] = useState(0)

  const debouncedSearch = useDebounce(search, 350)

  const { data, isLoading, isError, isFetching } = useFolderBookmarks(id ?? '', {
    page,
    search: debouncedSearch,
    sort,
    filter,
  })
  const { data: foldersData } = useFolders()
  const { data: tagsData } = useTags()
  const deleteMutation = useDeleteBookmark()
  const markAsReadMutation = useMarkAsRead()
  const addTagMutation = useAddTagToBookmark()
  const removeTagMutation = useRemoveTagFromBookmark()
  const addToFolderMutation = useAddBookmarkToFolder()
  const removeFromFolderMutation = useRemoveBookmarkFromFolder()

  async function handleDelete(bookmarkId: string) {
    setDeletingId(bookmarkId)
    try {
      await deleteMutation.mutateAsync(bookmarkId)
    } finally {
      setDeletingId(null)
    }
  }

  async function handleToggleRead(bookmarkId: string, isRead: boolean) {
    await markAsReadMutation.mutateAsync({ bookmarkId, isRead })
  }

  async function handleAddTag(bookmarkId: string, tagId: string) {
    await addTagMutation.mutateAsync({ bookmarkId, tagId })
  }

  async function handleRemoveTag(bookmarkId: string, tagId: string) {
    await removeTagMutation.mutateAsync({ bookmarkId, tagId })
  }

  async function handleAddToFolder(bookmarkId: string, folderId: string) {
    await addToFolderMutation.mutateAsync({ bookmarkId, folderId })
  }

  async function handleRemoveFromFolder(bookmarkId: string, folderId: string) {
    await removeFromFolderMutation.mutateAsync({ bookmarkId, folderId })
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
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border-subtle px-4 sm:px-6">
        <SidebarTrigger className="text-text-muted hover:text-text-primary" />
        <Link
          to="/dashboard/folders"
          className="flex items-center gap-1 text-sm text-text-muted transition-colors hover:text-text-primary"
        >
          <ChevronLeft size={14} />
          Folders
        </Link>
        <span className="text-border-subtle">/</span>
        <h1 className="font-serif italic text-lg text-text-primary">Folder</h1>
      </header>

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
            emptyMessage="This folder is empty"
            emptyDescription="Move bookmarks here to organize them."
            onAddBookmark={() => navigate('/dashboard')}
          />
        </div>

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
