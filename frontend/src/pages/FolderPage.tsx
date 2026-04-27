import { useState, useRef, useEffect } from 'react'
import { useParams, Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Input } from '@/components/ui/input'
import BookmarkFeed from '@/components/bookmarks/BookmarkFeed'
import BookmarkToolbar from '@/components/bookmarks/BookmarkToolbar'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'
import {
  useFolderBookmarks,
  useFolder,
  useDeleteBookmark,
  useMarkAsRead,
  useFolders,
  useTags,
  useAddTagToBookmark,
  useRemoveTagFromBookmark,
  useAddBookmarkToFolder,
  useRemoveBookmarkFromFolder,
  useUpdateFolder,
} from '@/features/bookmarks/hooks'
import { useDebounce } from '@/hooks/useDebounce'
import type { SortOption, FilterState } from '@/types'

export default function FolderPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<SortOption>('date-desc')
  const [filter, setFilter] = useState<FilterState>({ tagIds: [] })
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const page = Number(searchParams.get('page')) || 0
  const [isEditing, setIsEditing] = useState(false)
  const [editName, setEditName] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const debouncedSearch = useDebounce(search, 350)

  const { data: bookmarksData, isLoading, isError, isFetching } = useFolderBookmarks(id ?? '', {
    page,
    search: debouncedSearch,
    sort,
    filter,
  })
  const { data: folderData } = useFolder(id ?? '')
  const { data: tagsData } = useTags()
  const { data: foldersData } = useFolders()
  const deleteMutation = useDeleteBookmark()
  const markAsReadMutation = useMarkAsRead()
  const addTagMutation = useAddTagToBookmark()
  const removeTagMutation = useRemoveTagFromBookmark()
  const addToFolderMutation = useAddBookmarkToFolder()
  const removeFromFolderMutation = useRemoveBookmarkFromFolder()
  const updateFolderMutation = useUpdateFolder()

  const folderName = folderData?.name ?? 'Folder'
  const bookmarkCount = folderData?.bookmarkCount ?? 0

  async function handleDelete(bookmarkId: string) {
    setDeletingId(bookmarkId)
    try {
      await deleteMutation.mutateAsync(bookmarkId)
      toast.success('Bookmark deleted')
    } catch {
      toast.error('Failed to delete bookmark')
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

  function handleSearchChange(value: string) {
    setSearch(value)
    setSearchParams((prev) => {
      prev.set('page', '0')
      return prev
    })
  }

  function handleSortChange(value: SortOption) {
    setSort(value)
    setSearchParams((prev) => {
      prev.set('page', '0')
      return prev
    })
  }

  function handleFilterChange(value: FilterState) {
    setFilter(value)
    setSearchParams((prev) => {
      prev.set('page', '0')
      return prev
    })
  }

  const hasMore = bookmarksData?.pagination.hasMore ?? false

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isEditing])

  function handleStartEdit() {
    setEditName(folderName)
    setIsEditing(true)
  }

  async function handleSaveEdit() {
    if (!editName.trim() || editName === folderName) {
      setIsEditing(false)
      return
    }
    try {
      await updateFolderMutation.mutateAsync({ folderId: id!, name: editName.trim() })
      toast.success('Folder renamed')
      setIsEditing(false)
    } catch {
      toast.error('Failed to rename folder')
    }
  }

  function handleCancelEdit() {
    setIsEditing(false)
    setEditName('')
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') {
      handleSaveEdit()
    } else if (e.key === 'Escape') {
      handleCancelEdit()
    }
  }

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
        {isEditing ? (
          <Input
            ref={inputRef}
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={handleSaveEdit}
            className="h-7 w-32 font-serif text-lg italic"
          />
        ) : (
          <h1
            onClick={handleStartEdit}
            className="cursor-pointer font-serif italic text-lg text-text-primary hover:underline"
          >
            {folderName}
          </h1>
        )}
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
          totalCount={bookmarkCount}
        />

        <div className="mt-6">
          <BookmarkFeed
            bookmarks={bookmarksData?.data}
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
            inFolderContext={true}
            currentFolderId={id}
          />
        </div>

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
