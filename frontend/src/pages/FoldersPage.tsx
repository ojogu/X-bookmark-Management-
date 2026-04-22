import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Folder, FolderOpen, Plus, Trash2, X } from 'lucide-react'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { toast } from 'sonner'
import { useFolders, useCreateFolder, useDeleteFolder } from '@/features/bookmarks/hooks'
import type { Folder as FolderType } from '@/types'

export default function FoldersPage() {
  const [isCreating, setIsCreating] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const { data: folders, isLoading, isError } = useFolders()
  const createFolder = useCreateFolder()
  const deleteFolder = useDeleteFolder()

  async function handleCreateFolder() {
    if (!newFolderName.trim()) return
    try {
      await createFolder.mutateAsync(newFolderName.trim())
      setNewFolderName('')
      setIsCreating(false)
      toast.success('Folder created')
    } catch {
      toast.error('Failed to create folder')
    }
  }

  async function handleDeleteFolder(id: string) {
    setDeletingId(id)
    try {
      await deleteFolder.mutateAsync(id)
      toast.success('Folder deleted')
    } catch {
      toast.error('Failed to delete folder')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border-subtle px-4 sm:px-6">
        <SidebarTrigger className="text-text-muted hover:text-text-primary" />
        <h1 className="font-serif italic text-lg text-text-primary">Folders</h1>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
        <div className="mb-6">
          {isCreating ? (
            <div className="flex items-center gap-2">
              <Input
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                placeholder="Folder name"
                className="h-9 max-w-xs border-border-subtle bg-bg-subtle"
                onKeyDown={(e) => e.key === 'Enter' && handleCreateFolder()}
                autoFocus
              />
              <Button
                size="sm"
                onClick={handleCreateFolder}
                disabled={!newFolderName.trim() || createFolder.isPending}
              >
                Create
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setIsCreating(false)
                  setNewFolderName('')
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
              New folder
            </Button>
          )}
        </div>

        {isLoading && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-xl" />
            ))}
          </div>
        )}

        {isError && <p className="text-sm text-text-muted">Failed to load folders.</p>}

        {!isLoading && folders && folders.length === 0 && (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-bg-subtle">
              <FolderOpen size={24} className="text-text-muted" />
            </div>
            <p className="text-sm font-medium text-text-primary">No folders yet</p>
            <p className="mt-1 text-xs text-text-muted">
              Folders help you group and organize your bookmarks.
            </p>
          </div>
        )}

        {folders && folders.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {folders.map((folder: FolderType) => (
              <div
                key={folder.id}
                className={`group relative flex flex-col gap-3 rounded-xl border border-border-subtle bg-bg-card p-5 transition-colors hover:border-border-strong ${
                  deletingId === folder.id ? 'pointer-events-none opacity-50' : ''
                }`}
              >
                <Link
                  to={`/dashboard/folders/${folder.id}`}
                  className="flex flex-1 flex-col gap-3"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-light text-brand-mid">
                    <Folder size={18} />
                  </div>
                  <div>
                    <p className="font-medium text-text-primary">{folder.name}</p>
                    <p className="text-xs text-text-muted">
                      {folder.bookmarkCount} bookmark{folder.bookmarkCount !== 1 ? 's' : ''}
                    </p>
                  </div>
                </Link>

                <button
                  onClick={() => handleDeleteFolder(folder.id)}
                  className="absolute right-3 top-3 flex h-7 w-7 items-center justify-center rounded-lg text-text-muted opacity-0 transition-all hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                  title="Delete folder"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}