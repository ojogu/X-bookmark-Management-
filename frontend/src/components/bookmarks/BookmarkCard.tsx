import { useState } from 'react'
import { Trash2, Check, Circle, MoreHorizontal, Folder, Tag, X } from 'lucide-react'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { formatRelativeTime } from '@/lib/utils'
import type { Bookmark, Folder as FolderType, Tag as TagType } from '@/types'

interface BookmarkCardProps {
  bookmark: Bookmark
  onDelete: (id: string) => void
  onToggleRead?: (id: string, isRead: boolean) => void
  onAddToFolder?: (bookmarkId: string, folderId: string) => void
  onRemoveFromFolder?: (bookmarkId: string, folderId: string) => void
  onAddTag?: (bookmarkId: string, tagId: string) => void
  onRemoveTag?: (bookmarkId: string, tagId: string) => void
  availableFolders?: FolderType[]
  availableTags?: TagType[]
  bookmarkFolders?: string[]
  isDeleting?: boolean
}

export default function BookmarkCard({
  bookmark,
  onDelete,
  onToggleRead,
  onAddToFolder,
  onRemoveFromFolder,
  onAddTag,
  onRemoveTag,
  availableFolders = [],
  availableTags = [],
  bookmarkFolders = [],
  isDeleting,
}: BookmarkCardProps) {
  const { id, author, text, savedAt, tags, faviconUrl, isRead } = bookmark
  const [open, setOpen] = useState(false)

  return (
    <article
      className={`group relative rounded-xl border bg-card p-4 transition-colors hover:border-border-strong dark:bg-bg-card dark:border-border-subtle dark:hover:border-border-strong ${
        isRead ? 'border-border-subtle' : 'border-border-strong'
      } ${isDeleting ? 'pointer-events-none opacity-50' : ''}`}
    >
      {/* Unread indicator */}
      {!isRead && (
        <span className="absolute left-3.5 top-4 h-1.5 w-1.5 rounded-full bg-brand" />
      )}

      {/* Author row */}
      <div className="mb-3 flex items-center gap-2 pl-4">
        <Avatar className="h-6 w-6 shrink-0">
          <AvatarImage src={author.avatarUrl ?? undefined} alt={author.name} />
          <AvatarFallback className="bg-muted text-[10px] text-muted-foreground dark:bg-bg-subtle dark:text-text-muted">
            {author.name.slice(0, 2).toUpperCase()}
          </AvatarFallback>
        </Avatar>

        <span className="text-sm font-medium text-card-foreground dark:text-text-primary">{author.name}</span>
        <span className="text-xs text-muted-foreground dark:text-text-muted">@{author.handle}</span>

        {faviconUrl && (
          <>
            <span className="text-xs text-muted-foreground dark:text-text-muted">·</span>
            <img src={faviconUrl} alt="" className="h-3.5 w-3.5 rounded-sm" />
          </>
        )}

        <span className="ml-auto text-xs text-muted-foreground dark:text-text-muted">{formatRelativeTime(savedAt)}</span>
      </div>

      {/* Tweet text */}
      <p className="line-clamp-4 text-sm leading-relaxed text-card-foreground dark:text-text-primary pl-4">{text}</p>

      {/* Footer — tags + actions */}
      <div className="mt-3 flex items-center gap-1.5 pl-4">
        {tags.slice(0, 4).map((tag) => (
          <Badge
            key={tag.id}
            variant="secondary"
            className="border-0 bg-brand-light px-2 py-0.5 text-[10px] font-medium text-brand-mid"
          >
            #{tag.name}
          </Badge>
        ))}
        {tags.length > 4 && (
          <span className="text-xs text-muted-foreground dark:text-text-muted">+{tags.length - 4}</span>
        )}

        {/* Actions dropdown */}
        <DropdownMenu open={open} onOpenChange={setOpen}>
          <DropdownMenuTrigger asChild>
            <button
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-muted-foreground dark:text-text-muted transition-all hover:bg-muted dark:hover:bg-bg-subtle ml-auto"
              title="More actions"
            >
              <MoreHorizontal size={13} />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            {/* Mark as read/unread */}
            {onToggleRead && (
              <DropdownMenuItem onClick={() => onToggleRead(id, !isRead)}>
                {isRead ? (
                  <>
                    <Circle size={14} className="mr-2" />
                    Mark as unread
                  </>
                ) : (
                  <>
                    <Check size={14} className="mr-2" />
                    Mark as read
                  </>
                )}
              </DropdownMenuItem>
            )}

            {/* Add to folder submenu */}
            {onAddToFolder && availableFolders.length > 0 && (
              <DropdownMenuSub>
                <DropdownMenuSubTrigger>
                  <Folder size={14} className="mr-2" />
                  Add to folder
                </DropdownMenuSubTrigger>
                <DropdownMenuSubContent>
                  {availableFolders.map((folder) => {
                    const isInFolder = bookmarkFolders.includes(folder.id)
                    return (
                      <DropdownMenuItem
                        key={folder.id}
                        onClick={() => {
                          if (isInFolder && onRemoveFromFolder) {
                            onRemoveFromFolder(id, folder.id)
                          } else {
                            onAddToFolder(id, folder.id)
                          }
                          setOpen(false)
                        }}
                      >
                        {isInFolder && <X size={14} className="mr-2" />}
                        {folder.name}
                        {isInFolder && <span className="ml-auto text-xs">✓</span>}
                      </DropdownMenuItem>
                    )
                  })}
                </DropdownMenuSubContent>
              </DropdownMenuSub>
            )}

            {/* Add tag submenu */}
            {onAddTag && availableTags.length > 0 && (
              <DropdownMenuSub>
                <DropdownMenuSubTrigger>
                  <Tag size={14} className="mr-2" />
                  Add tag
                </DropdownMenuSubTrigger>
                <DropdownMenuSubContent>
                  {availableTags.map((tag) => {
                    const hasTag = tags.some((t) => t.id === tag.id)
                    return (
                      <DropdownMenuItem
                        key={tag.id}
                        onClick={() => {
                          if (hasTag && onRemoveTag) {
                            onRemoveTag(id, tag.id)
                          } else {
                            onAddTag(id, tag.id)
                          }
                          setOpen(false)
                        }}
                      >
                        #{tag.name}
                        {hasTag && <span className="ml-auto text-xs">✓</span>}
                      </DropdownMenuItem>
                    )
                  })}
                </DropdownMenuSubContent>
              </DropdownMenuSub>
            )}

            <DropdownMenuSeparator />

            {/* Delete */}
            <DropdownMenuItem
              onClick={() => onDelete(id)}
              className="text-destructive focus:text-destructive"
            >
              <Trash2 size={14} className="mr-2" />
              Delete bookmark
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </article>
  )
}
