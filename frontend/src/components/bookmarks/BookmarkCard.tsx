import { useState } from 'react'
import { Trash2, Check, Circle, MoreHorizontal, Folder, FolderPlus, Tag, X, Quote } from 'lucide-react'
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
import type { Bookmark, Folder as FolderType, Tag as TagType, TweetType } from '@/types'
import { CreateFolderDialog } from '@/components/folders/CreateFolderDialog'

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
  onCreateFolder?: (callback: (folderId: string) => void) => void
  inFolderContext?: boolean
  currentFolderId?: string
  inTagContext?: boolean
  currentTagId?: string
}

const openTweet = (tweetId: string) => {
  const appUrl = `twitter://status?id=${tweetId}`
  const webUrl = `https://x.com/i/web/status/${tweetId}`

  window.location.href = appUrl

  setTimeout(() => {
    window.location.href = webUrl
  }, 1500)
}

function PlainBody({ bookmark }: { bookmark: Bookmark }) {
  const { author, text, savedAt, faviconUrl } = bookmark
  return (
    <>
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
      {text && (
        <p className="line-clamp-4 pl-4 text-sm leading-relaxed text-card-foreground dark:text-text-primary">{text}</p>
      )}
    </>
  )
}

function MediaBody({ bookmark }: { bookmark: Bookmark }) {
  const { author, text, savedAt, faviconUrl, media } = bookmark

  const isVideo = media?.type === 'video' || media?.type === 'animated_gif'
  const imageUrl = isVideo ? media?.preview_image_url : media?.url

  return (
    <>
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
      {text && (
        <p className="mb-2 pl-4 text-sm leading-relaxed text-card-foreground dark:text-text-primary">{text}</p>
      )}
      {imageUrl && (
        <div className="pl-4">
          <img
            src={imageUrl}
            alt={media?.alt_text ?? ''}
            className="max-h-80 w-full rounded-lg object-cover"
          />
        </div>
      )}
    </>
  )
}

function RetweetBody({ bookmark }: { bookmark: Bookmark }) {
  const { author, savedAt, referencedTweet } = bookmark

  return (
    <>
      <div className="mb-3 flex items-center gap-2 pl-4">
        <Avatar className="h-6 w-6 shrink-0">
          <AvatarImage src={author.avatarUrl ?? undefined} alt={author.name} />
          <AvatarFallback className="bg-muted text-[10px] text-muted-foreground dark:bg-bg-subtle dark:text-text-muted">
            {author.name.slice(0, 2).toUpperCase()}
          </AvatarFallback>
        </Avatar>
        <span className="text-sm font-medium text-card-foreground dark:text-text-primary">{author.name}</span>
        <span className="text-xs text-muted-foreground dark:text-text-muted">@{author.handle}</span>
        <span className="text-xs text-muted-foreground dark:text-text-muted">·</span>
        <span className="text-xs text-muted-foreground dark:text-text-muted">retweeted</span>
        <span className="ml-auto text-xs text-muted-foreground dark:text-text-muted">{formatRelativeTime(savedAt)}</span>
      </div>
      {referencedTweet ? (
        <div className="pl-4">
          <div className="flex items-center gap-2">
            <Avatar className="h-5 w-5 shrink-0">
              <AvatarImage src={referencedTweet.author.avatarUrl ?? undefined} alt={referencedTweet.author.name} />
              <AvatarFallback className="bg-muted text-[10px] text-muted-foreground dark:bg-bg-subtle dark:text-text-muted">
                {referencedTweet.author.name.slice(0, 2).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <span className="text-xs font-medium text-card-foreground dark:text-text-primary">{referencedTweet.author.name}</span>
            <span className="text-xs text-muted-foreground dark:text-text-muted">@{referencedTweet.author.handle}</span>
          </div>
          {referencedTweet.text && (
            <p className="mt-1 line-clamp-4 text-sm leading-relaxed text-card-foreground dark:text-text-primary">{referencedTweet.text}</p>
          )}
        </div>
      ) : (
        <div className="pl-4">
          <p className="text-sm italic text-muted-foreground dark:text-text-muted">This tweet is unavailable</p>
        </div>
      )}
    </>
  )
}

function QuoteBody({ bookmark }: { bookmark: Bookmark }) {
  const { author, text, savedAt, faviconUrl, referencedTweet } = bookmark

  return (
    <>
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
      {text && (
        <p className="mb-2 pl-4 text-sm leading-relaxed text-card-foreground dark:text-text-primary">{text}</p>
      )}
      <div className="pl-4">
        <div className="rounded-lg border border-border-subtle p-3 dark:border-border-subtle">
          <div className="mb-1 flex items-center gap-2">
            <Quote size={12} className="shrink-0 text-muted-foreground dark:text-text-muted" />
            <span className="text-xs text-muted-foreground dark:text-text-muted">quoted tweet</span>
          </div>
          {referencedTweet ? (
            <>
              <div className="flex items-center gap-2">
                <Avatar className="h-5 w-5 shrink-0">
                  <AvatarImage src={referencedTweet.author.avatarUrl ?? undefined} alt={referencedTweet.author.name} />
                  <AvatarFallback className="bg-muted text-[10px] text-muted-foreground dark:bg-bg-subtle dark:text-text-muted">
                    {referencedTweet.author.name.slice(0, 2).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <span className="text-xs font-medium text-card-foreground dark:text-text-primary">{referencedTweet.author.name}</span>
                <span className="text-xs text-muted-foreground dark:text-text-muted">@{referencedTweet.author.handle}</span>
              </div>
              {referencedTweet.text && (
                <p className="mt-1 line-clamp-3 text-sm leading-relaxed text-card-foreground dark:text-text-primary">{referencedTweet.text}</p>
              )}
            </>
          ) : (
            <p className="text-sm italic text-muted-foreground dark:text-text-muted">This tweet is unavailable</p>
          )}
        </div>
      </div>
    </>
  )
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
  onCreateFolder,
  inFolderContext = false,
  currentFolderId,
  inTagContext = false,
  currentTagId,
}: BookmarkCardProps) {
  const { id, isRead, tags } = bookmark
  const [open, setOpen] = useState(false)
  const [createFolderOpen, setCreateFolderOpen] = useState(false)

  const tweetType = (bookmark.tweetType || 'plain') as TweetType

  return (
    <div
      onClick={() => openTweet(bookmark.tweetId)}
      style={{ cursor: 'pointer' }}
    >
      <article
        className={`group relative rounded-xl border bg-card p-4 transition-colors hover:border-border-strong dark:bg-bg-card dark:border-border-subtle dark:hover:border-border-strong ${
          isRead ? 'border-border-subtle' : 'border-border-strong'
        } ${isDeleting ? 'pointer-events-none opacity-50' : ''}`}
      >
        {!isRead && (
          <span className="absolute left-3.5 top-4 h-1.5 w-1.5 rounded-full bg-brand" />
        )}

        {tweetType === 'media' && <MediaBody bookmark={bookmark} />}
        {tweetType === 'retweet' && <RetweetBody bookmark={bookmark} />}
        {tweetType === 'quote' && <QuoteBody bookmark={bookmark} />}
        {tweetType === 'plain' && <PlainBody bookmark={bookmark} />}

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

          <DropdownMenu open={open} onOpenChange={setOpen}>
            <DropdownMenuTrigger asChild>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                }}
                className="ml-auto flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-all hover:bg-muted dark:text-text-muted dark:hover:bg-bg-subtle"
                title="More actions"
              >
                <MoreHorizontal size={13} />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
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

              {inFolderContext && onRemoveFromFolder && currentFolderId ? (
                <DropdownMenuItem
                  onClick={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    onRemoveFromFolder(id, currentFolderId)
                    setOpen(false)
                  }}
                >
                  <X size={14} className="mr-2" />
                  Remove from folder
                </DropdownMenuItem>
              ) : (onAddToFolder || onCreateFolder) && (
                <DropdownMenuSub>
                  <DropdownMenuSubTrigger>
                    <Folder size={14} className="mr-2" />
                    Add to folder
                  </DropdownMenuSubTrigger>
                  <DropdownMenuSubContent>
                    {availableFolders.length > 0 ? (
                      availableFolders.map((folder) => {
                        const isInFolder = bookmarkFolders.includes(folder.id)
                        return (
                          <DropdownMenuItem
                            key={folder.id}
                            onClick={(e) => {
                              e.preventDefault()
                              e.stopPropagation()
                              if (isInFolder && onRemoveFromFolder) {
                                onRemoveFromFolder(id, folder.id)
                              } else {
                                onAddToFolder?.(id, folder.id)
                              }
                              setOpen(false)
                            }}
                          >
                            {isInFolder && <X size={14} className="mr-2" />}
                            {folder.name}
                            {isInFolder && <span className="ml-auto text-xs">✓</span>}
                          </DropdownMenuItem>
                        )
                      })
                    ) : (
                      <DropdownMenuItem disabled className="text-muted-foreground">
                        No folders yet
                      </DropdownMenuItem>
                    )}
                    {onCreateFolder && (
                      <>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.preventDefault()
                            e.stopPropagation()
                            setOpen(false)
                            setCreateFolderOpen(true)
                          }}
                          className="text-muted-foreground cursor-pointer"
                        >
                          <FolderPlus size={14} className="mr-2" />
                          Create folder
                        </DropdownMenuItem>
                      </>
                    )}
                  </DropdownMenuSubContent>
                </DropdownMenuSub>
              )}

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
                          onClick={(e) => {
                            e.preventDefault()
                            e.stopPropagation()
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

              {inTagContext && onRemoveTag && currentTagId && (
                <DropdownMenuItem
                  onClick={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    onRemoveTag(id, currentTagId)
                    setOpen(false)
                  }}
                >
                  <X size={14} className="mr-2" />
                  Remove tag
                </DropdownMenuItem>
              )}

              <DropdownMenuSeparator />

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

      <CreateFolderDialog
        open={createFolderOpen}
        onOpenChange={setCreateFolderOpen}
        onCreated={(folderId) => {
          onAddToFolder?.(id, folderId)
        }}
      />
    </div>
  )
}