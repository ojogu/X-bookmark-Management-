export interface BookmarkAuthor {
  id: string
  name: string
  handle: string // without @
  avatarUrl: string | null
  verified: boolean
}

export interface Tag {
  id: string
  name: string
  color?: string
  source?: 'user' | 'x'
  bookmarkCount: number
}

export interface Folder {
  id: string
  name: string
  bookmarkCount: number
}

export interface Bookmark {
  id: string
  tweetId: string
  text: string
  author: BookmarkAuthor
  savedAt: string // ISO date string
  isRead: boolean
  tags: Tag[]
  folder: Folder | null
  url: string
  faviconUrl?: string
  mediaUrls?: string[]
}

export interface UserProfile {
  id: string
  username: string
  name: string
  profile_image_url: string | null
  description: string | null
  followers_count: number
  following_count: number
  tweet_count: number
  verified: boolean
  location: string | null
}

export type SortOption = 'date-desc' | 'date-asc' | 'alpha-asc' | 'alpha-desc'

export interface FilterState {
  tagIds: string[]
  folderId?: string
}

export interface PaginatedResponse<T> {
  data: T[]
  pagination: {
    page: number
    pageSize: number
    total: number
    hasMore: boolean
  }
}
