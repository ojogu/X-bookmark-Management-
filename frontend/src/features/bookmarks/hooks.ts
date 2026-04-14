import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import client from '@/api/client'
import type {
  Bookmark,
  Folder,
  Tag,
  UserProfile,
  SortOption,
  FilterState,
  PaginatedResponse,
} from '@/types'

// ── Query keys ───────────────────────────────────────────────────
export const bookmarkKeys = {
  all: ['bookmarks'] as const,
  lists: () => [...bookmarkKeys.all, 'list'] as const,
  list: (filters: Record<string, unknown>) => [...bookmarkKeys.lists(), filters] as const,
  unread: () => [...bookmarkKeys.all, 'unread'] as const,
  folders: ['folders'] as const,
  folder: (id: string) => [...bookmarkKeys.folders, id] as const,
  tags: ['tags'] as const,
  profile: ['profile'] as const,
}

// ── Bookmarks ─────────────────────────────────────────────────────
interface UseBookmarksOptions {
  search?: string
  sort?: SortOption
  filter?: FilterState
  page?: number
}

export function useBookmarks(options: UseBookmarksOptions = {}) {
  const { search = '', sort = 'date-desc', filter = { tagIds: [] }, page = 0 } = options

  return useQuery({
    queryKey: bookmarkKeys.list({ search, sort, filter, page }),
    queryFn: async () => {
      const limit = 20
      const offset = page * limit
      const params = new URLSearchParams()
      params.set('limit', String(limit))
      params.set('offset', String(offset))
      if (search) params.set('search', search)
      if (sort) params.set('sort', sort)
      if (filter.tagIds.length) params.set('tags', filter.tagIds.join(','))
      if (filter.folderId) params.set('folder_id', filter.folderId)

      const res = await client.get<{
        data: Bookmark[]
        meta: { result_count: number; total_count: number; next_token: string | null }
      }>(`/client/bookmarks?${params}`)
      
      // Transform backend response to frontend format
      const response = res.data
      return {
        data: response.data,
        pagination: {
          page,
          pageSize: limit,
          total: response.meta.total_count,
          hasMore: !!response.meta.next_token,
        },
      }
    },
  })
}

// ── Unread bookmarks ──────────────────────────────────────────────
export function useUnreadBookmarks(page: number = 0) {
  return useQuery({
    queryKey: bookmarkKeys.unread(),
    queryFn: async () => {
      const limit = 20
      const offset = page * limit
      const res = await client.get<{
        data: Bookmark[]
        meta: { result_count: number; total_count: number; next_token: string | null }
      }>(`/client/bookmarks?unread=true&limit=${limit}&offset=${offset}`)
      
      const response = res.data
      return {
        data: response.data,
        pagination: {
          page,
          pageSize: limit,
          total: response.meta.total_count,
          hasMore: !!response.meta.next_token,
        },
      }
    },
  })
}

// ── Delete bookmark ───────────────────────────────────────────────
export function useDeleteBookmark() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async (bookmarkId: string) => {
      await client.delete(`/client/bookmarks/${bookmarkId}`)
    },
    onMutate: async (bookmarkId) => {
      // Optimistic: remove from all list queries
      await qc.cancelQueries({ queryKey: bookmarkKeys.lists() })
      const snapshots = qc.getQueriesData<PaginatedResponse<Bookmark>>({ queryKey: bookmarkKeys.lists() })

      qc.setQueriesData<PaginatedResponse<Bookmark>>(
        { queryKey: bookmarkKeys.lists() },
        (old) => {
          if (!old) return old
          return { ...old, data: old.data.filter((b) => b.id !== bookmarkId) }
        },
      )

      return { snapshots }
    },
    onError: (_err, _id, ctx) => {
      // Rollback on error
      ctx?.snapshots.forEach(([key, data]) => qc.setQueryData(key, data))
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: bookmarkKeys.lists() })
      qc.invalidateQueries({ queryKey: bookmarkKeys.unread() })
    },
  })
}

// ── Mark as read ───────────────────────────────────────────────
export function useMarkAsRead() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async ({ bookmarkId, isRead }: { bookmarkId: string; isRead: boolean }) => {
      await client.patch(`/client/bookmarks/${bookmarkId}/read`, { is_read: isRead })
    },
    onMutate: async ({ bookmarkId, isRead }) => {
      await qc.cancelQueries({ queryKey: bookmarkKeys.lists() })
      const snapshots = qc.getQueriesData<PaginatedResponse<Bookmark>>({ queryKey: bookmarkKeys.lists() })

      qc.setQueriesData<PaginatedResponse<Bookmark>>(
        { queryKey: bookmarkKeys.lists() },
        (old) => {
          if (!old) return old
          return {
            ...old,
            data: old.data.map((b) =>
              b.id === bookmarkId ? { ...b, isRead } : b
            ),
          }
        },
      )

      return { snapshots }
    },
    onError: (_err, _vars, ctx) => {
      ctx?.snapshots.forEach(([key, data]) => qc.setQueryData(key, data))
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: bookmarkKeys.lists() })
      qc.invalidateQueries({ queryKey: bookmarkKeys.unread() })
    },
  })
}

// ── Folders ───────────────────────────────────────────────────────
export function useFolders() {
  return useQuery({
    queryKey: bookmarkKeys.folders,
    queryFn: async () => {
      const res = await client.get<Folder[]>('/client/folders')
      return res.data
    },
  })
}

export function useFolderBookmarks(folderId: string, page: number = 0) {
  return useQuery({
    queryKey: bookmarkKeys.folder(folderId),
    queryFn: async () => {
      const limit = 20
      const offset = page * limit
      const res = await client.get<{
        data: Bookmark[]
        meta: { result_count: number; total_count: number; next_token: string | null }
      }>(`/client/bookmarks?folder_id=${folderId}&limit=${limit}&offset=${offset}`)

      const response = res.data
      return {
        data: response.data,
        pagination: {
          page,
          pageSize: limit,
          total: response.meta.total_count,
          hasMore: !!response.meta.next_token,
        },
      }
    },
    enabled: !!folderId,
  })
}

// ── Folder CRUD ─────────────────────────────────────────────────
export function useCreateFolder() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async (name: string) => {
      const res = await client.post<Folder>('/client/folders', { name })
      return res.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: bookmarkKeys.folders })
    },
  })
}

export function useUpdateFolder() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async ({ folderId, name }: { folderId: string; name: string }) => {
      const res = await client.put<Folder>(`/client/folders/${folderId}`, { name })
      return res.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: bookmarkKeys.folders })
    },
  })
}

export function useDeleteFolder() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async (folderId: string) => {
      await client.delete(`/client/folders/${folderId}`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: bookmarkKeys.folders })
    },
  })
}

// ── Tags ──────────────────────────────────────────────────────────
export function useTags() {
  return useQuery({
    queryKey: bookmarkKeys.tags,
    queryFn: async () => {
      const res = await client.get<Tag[]>('/client/tags')
      return res.data
    },
  })
}

// ── Tag CRUD ────────────────────────────────────────────────────
export function useCreateTag() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async ({ name, color }: { name: string; color?: string }) => {
      const res = await client.post<Tag>('/client/tags', { name, color })
      return res.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: bookmarkKeys.tags })
    },
  })
}

export function useUpdateTag() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async ({ tagId, name, color }: { tagId: string; name?: string; color?: string }) => {
      const res = await client.put<Tag>(`/client/tags/${tagId}`, { name, color })
      return res.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: bookmarkKeys.tags })
    },
  })
}

export function useDeleteTag() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async (tagId: string) => {
      await client.delete(`/client/tags/${tagId}`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: bookmarkKeys.tags })
    },
  })
}

// ── User profile ──────────────────────────────────────────────────
export function useProfile() {
  return useQuery({
    queryKey: bookmarkKeys.profile,
    queryFn: async () => {
      const res = await client.get<UserProfile>('/client/info')
      return res.data
    },
    staleTime: 5 * 60 * 1000,
  })
}

// ── Onboarding: fetch fresh user info from X ────────────────────
export function useFetchUserInfoFresh() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const res = await client.get<UserProfile>('/X/user-info/fresh')
      return res.data
    },
    retry: 3,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: bookmarkKeys.profile })
    },
  })
}

// ── Onboarding: trigger initial bookmark sync ────────────────────
export function useTriggerSync() {
  return useMutation({
    mutationFn: async () => {
      const res = await client.post<{ status: string; message: string }>('/client/sync')
      return res.data
    },
    retry: 3,
  })
}

// ── Bookmark folder management ─────────────────────────────────
export function useAddBookmarkToFolder() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async ({ bookmarkId, folderId }: { bookmarkId: string; folderId: string }) => {
      await client.post(`/client/bookmarks/${bookmarkId}/folders`, { folder_id: folderId })
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: bookmarkKeys.lists() })
    },
  })
}

export function useRemoveBookmarkFromFolder() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async ({ bookmarkId, folderId }: { bookmarkId: string; folderId: string }) => {
      await client.delete(`/client/bookmarks/${bookmarkId}/folders/${folderId}`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: bookmarkKeys.lists() })
    },
  })
}

export function useGetBookmarkFolders(bookmarkId: string) {
  return useQuery({
    queryKey: ['bookmark-folders', bookmarkId],
    queryFn: async () => {
      const res = await client.get<{ id: string; name: string }[]>(`/client/bookmarks/${bookmarkId}/folders`)
      return res.data
    },
    enabled: !!bookmarkId,
  })
}

// ── Bookmark tag management ────────────────────────────────────
export function useAddTagToBookmark() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async ({ bookmarkId, tagId }: { bookmarkId: string; tagId: string }) => {
      await client.post(`/client/bookmarks/${bookmarkId}/tags`, { tag_id: tagId })
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: bookmarkKeys.lists() })
    },
  })
}

export function useRemoveTagFromBookmark() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async ({ bookmarkId, tagId }: { bookmarkId: string; tagId: string }) => {
      await client.delete(`/client/bookmarks/${bookmarkId}/tags/${tagId}`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: bookmarkKeys.lists() })
    },
  })
}

export function useGetBookmarkTags(bookmarkId: string) {
  return useQuery({
    queryKey: ['bookmark-tags', bookmarkId],
    queryFn: async () => {
      const res = await client.get<{ id: string; name: string; color?: string }[]>(`/client/bookmarks/${bookmarkId}/tags`)
      return res.data
    },
    enabled: !!bookmarkId,
  })
}
