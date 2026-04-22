import { useState } from 'react'
import { FolderPlus, X } from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'
import { useCreateFolder } from '@/features/bookmarks/hooks'

interface CreateFolderDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated?: (folderId: string) => void
}

export function CreateFolderDialog({
  open,
  onOpenChange,
  onCreated,
}: CreateFolderDialogProps) {
  const [name, setName] = useState('')
  const createFolder = useCreateFolder()

  async function handleCreate() {
    if (!name.trim()) return
    try {
      const folder = await createFolder.mutateAsync(name.trim())
      setName('')
      onOpenChange(false)
      onCreated?.(folder.id)
    } catch {
      toast.error('Failed to create folder')
    }
  }

  function handleClose() {
    setName('')
    onOpenChange(false)
  }

  return (
    <Sheet open={open} onOpenChange={handleClose}>
      <SheetContent side="bottom" className="mx-auto mb-24 w-full max-w-md rounded-t-2xl sm:max-w-lg">
        <SheetHeader className="relative">
          <SheetTitle className="flex items-center gap-2">
            <FolderPlus size={18} />
            Create Folder
          </SheetTitle>
          <SheetDescription>
            Give your folder a name to organize your bookmarks.
          </SheetDescription>
          <Button
            variant="ghost"
            size="icon-sm"
            className="absolute right-0 top-0"
            onClick={handleClose}
          >
            <X size={16} />
          </Button>
        </SheetHeader>

        <div className="mt-4 flex gap-2">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Folder name"
            className="h-10 border-border-subtle bg-bg-subtle"
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            autoFocus
          />
          <Button
            onClick={handleCreate}
            disabled={!name.trim() || createFolder.isPending}
            className="h-10"
          >
            {createFolder.isPending ? 'Creating...' : 'Create'}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}