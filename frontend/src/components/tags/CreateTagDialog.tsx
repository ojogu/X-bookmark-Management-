import { useState } from 'react'
import { Tag as TagIcon, X } from 'lucide-react'
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
import { useCreateTag } from '@/features/bookmarks/hooks'

const TAG_COLORS = [
  '#ef4444', // red
  '#f97316', // orange
  '#eab308', // yellow
  '#22c55e', // green
  '#06b6d4', // cyan
  '#3b82f6', // blue
  '#8b5cf6', // violet
  '#ec4899', // pink
  '#6b7280', // gray
]

interface CreateTagDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated?: (tagId: string) => void
}

export function CreateTagDialog({
  open,
  onOpenChange,
  onCreated,
}: CreateTagDialogProps) {
  const [name, setName] = useState('')
  const [color, setColor] = useState(TAG_COLORS[5])
  const createTag = useCreateTag()

  async function handleCreate() {
    if (!name.trim()) return
    try {
      const tag = await createTag.mutateAsync({ name: name.trim(), color })
      setName('')
      setColor(TAG_COLORS[5])
      onOpenChange(false)
      onCreated?.(tag.id)
      toast.success('Tag created')
    } catch {
      toast.error('Failed to create tag')
    }
  }

  function handleClose() {
    setName('')
    setColor(TAG_COLORS[5])
    onOpenChange(false)
  }

  return (
    <Sheet open={open} onOpenChange={handleClose}>
      <SheetContent side="bottom" className="mx-auto mb-24 w-full max-w-md rounded-t-2xl sm:max-w-lg">
        <SheetHeader className="relative">
          <SheetTitle className="flex items-center gap-2">
            <TagIcon size={18} />
            Create Tag
          </SheetTitle>
          <SheetDescription>
            Give your tag a name and choose a color.
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

        <div className="mt-4 space-y-4">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Tag name"
            className="h-10 border-border-subtle bg-bg-subtle"
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            autoFocus
          />

          <div className="flex gap-2">
            {TAG_COLORS.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setColor(c)}
                className={`h-6 w-6 rounded-full transition-transform ${
                  color === c ? 'scale-125 ring-2 ring-offset-2 ring-black dark:ring-white' : 'hover:scale-110'
                }`}
                style={{ backgroundColor: c }}
              />
            ))}
          </div>

          <Button
            onClick={handleCreate}
            disabled={!name.trim() || createTag.isPending}
            className="w-full"
          >
            {createTag.isPending ? 'Creating...' : 'Create'}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}