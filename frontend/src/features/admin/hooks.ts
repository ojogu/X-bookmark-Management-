import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminApi } from '@/api/admin'

// ── Query keys ───────────────────────────────────────────────────
export const adminKeys = {
  stats: ['admin', 'stats'] as const,
  overview: () => [...adminKeys.stats, 'overview'] as const,
  signups: (range: string) => [...adminKeys.stats, 'signups', range] as const,
  bookmarks: (range: string) => [...adminKeys.stats, 'bookmarks', range] as const,
  users: ['admin', 'users'] as const,
  userList: (filters: Record<string, unknown>) => [...adminKeys.users, 'list', filters] as const,
  user: (id: string) => [...adminKeys.users, 'detail', id] as const,
  jobs: ['admin', 'jobs'] as const,
  jobList: (filters: Record<string, unknown>) => [...adminKeys.jobs, 'list', filters] as const,
  tokens: ['admin', 'tokens'] as const,
  tokenList: (page: number) => [...adminKeys.tokens, 'list', page] as const,
  health: ['admin', 'health'] as const,
  metrics: () => [...adminKeys.health, 'metrics'] as const,
  errorLogs: (level: string) => [...adminKeys.health, 'logs', level] as const,
  audit: ['admin', 'audit'] as const,
  auditLogs: (filters: Record<string, unknown>) => [...adminKeys.audit, 'list', filters] as const,
}

// ── Types ───────────────────────────────────────────────────
export interface StatsOverview {
  total_users: number
  total_users_daily: number
  total_users_weekly: number
  total_users_monthly: number
  active_users: number
  active_users_daily: number
  active_users_weekly: number
  active_users_monthly: number
  bookmarks_today: number
  bookmarks_daily: number
  bookmarks_weekly: number
  bookmarks_monthly: number
  jobs_today: number
  jobs_daily: number
  jobs_weekly: number
  jobs_monthly: number
}

export interface StatsDatePoint {
  date: string
  count: number
}

export interface UserListItem {
  id: string
  email: string | null
  username: string
  name: string
  role: string
  created_at: string
  bookmark_count: number
}

export interface UserDetail {
  id: string
  x_id: string
  email: string | null
  username: string
  name: string
  role: string
  created_at: string
  last_front_sync_time: string | null
  is_backfill_complete: boolean
  bookmark_count: number
}

export interface SyncJob {
  id: string
  task_id: string
  user_id: string
  type: string
  status: string
  started_at: string | null
  completed_at: string | null
  error: string | null
}

export interface OAuthToken {
  user_id: string
  username: string
  expires_at: string | null
  is_expired: boolean
  last_used: string | null
}

export interface HealthMetrics {
  api_p95_latency_ms: number
  celery_workers: number
  redis_memory_used_mb: number
  redis_memory_total_mb: number
  rabbitmq_queue_depth: number
}

export interface ErrorLog {
  id: string
  timestamp: string
  level: string
  message: string
  trace: string | null
  source: string
}

export interface AuditLog {
  id: string
  timestamp: string
  admin_id: string | null
  admin_email: string | null
  action: string
  resource: string
  ip_address: string | null
  details: Record<string, unknown> | null
}

// ── Stats ─────────────────────────────────────────────────────
export function useStatsOverview() {
  return useQuery({
    queryKey: adminKeys.overview(),
    queryFn: () => adminApi.get<StatsOverview>('/stats/overview'),
  })
}

export function useSignups(range = '30d') {
  return useQuery({
    queryKey: adminKeys.signups(range),
    queryFn: () => adminApi.get<StatsDatePoint[]>(`/stats/signups?range=${range}`),
  })
}

export function useBookmarks(range = '14d') {
  return useQuery({
    queryKey: adminKeys.bookmarks(range),
    queryFn: () => adminApi.get<StatsDatePoint[]>(`/stats/bookmarks?range=${range}`),
  })
}

// ── Users ───────────────────────────────────────────────────
interface UseUsersOptions {
  search?: string
  status?: string
  page?: number
  limit?: number
}

export function useAdminUsers(options: UseUsersOptions = {}) {
  const { search = '', status = '', page = 1, limit = 50 } = options

  return useQuery({
    queryKey: adminKeys.userList({ search, status, page, limit }),
    queryFn: () => {
      const params = new URLSearchParams()
      if (search) params.set('search', search)
      if (status) params.set('status', status)
      params.set('page', String(page))
      params.set('limit', String(limit))
      return adminApi.get<{ items: UserListItem[]; total: number; page: number; limit: number }>(
        `/users?${params}`
      )
    },
  })
}

export function useUserDetail(userId: string) {
  return useQuery({
    queryKey: adminKeys.user(userId),
    queryFn: () => adminApi.get<UserDetail>(`/users/${userId}`),
    enabled: !!userId,
  })
}

// ── Jobs ───────────────────────────────────────────────────
interface UseJobsOptions {
  status?: string
  type?: string
  page?: number
  limit?: number
}

export function useAdminJobs(options: UseJobsOptions = {}) {
  const { status = '', type = '', page = 1, limit = 50 } = options

  return useQuery({
    queryKey: adminKeys.jobList({ status, type, page, limit }),
    queryFn: () => {
      const params = new URLSearchParams()
      if (status) params.set('status', status)
      if (type) params.set('type', type)
      params.set('page', String(page))
      params.set('limit', String(limit))
      return adminApi.get<{ items: SyncJob[]; total: number; page: number; limit: number }>(
        `/jobs?${params}`
      )
    },
  })
}

// ── OAuth Tokens ──────────────────────────────────────────────
export function useOAuthTokens(page = 1, limit = 50) {
  return useQuery({
    queryKey: adminKeys.tokenList(page),
    queryFn: () =>
      adminApi.get<{ items: OAuthToken[]; total: number; page: number; limit: number }>(
        `/oauth/tokens?page=${page}&limit=${limit}`
      ),
  })
}

// ── Health ────────────────────────────────────────────────
export function useHealthMetrics() {
  return useQuery({
    queryKey: adminKeys.metrics(),
    queryFn: () => adminApi.get<HealthMetrics>('/health'),
    refetchInterval: 30000,
  })
}

export function useErrorLogs(level = 'error', limit = 50) {
  return useQuery({
    queryKey: adminKeys.errorLogs(level),
    queryFn: () =>
      adminApi.get<{ items: ErrorLog[]; total: number }>(
        `/health/logs?level=${level}&limit=${limit}`
      ),
  })
}

// ── Audit Logs ──────────────────────────────────────────────
interface UseAuditLogsOptions {
  action?: string
  page?: number
  limit?: number
}

export function useAuditLogs(options: UseAuditLogsOptions = {}) {
  const { action = '', page = 1, limit = 50 } = options

  return useQuery({
    queryKey: adminKeys.auditLogs({ action, page, limit }),
    queryFn: () => {
      const params = new URLSearchParams()
      if (action) params.set('action', action)
      params.set('page', String(page))
      params.set('limit', String(limit))
      return adminApi.get<{ items: AuditLog[]; total: number; page: number; limit: number }>(
        `/audit-logs?${params}`
      )
    },
  })
}

// ── Mutations ────────────────────────────────────────────
export function useSuspendUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (userId: string) =>
      adminApi.patch(`/users/${userId}/status`, { status: 'suspended' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.users })
    },
  })
}

export function useDeleteUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (userId: string) => adminApi.delete(`/users/${userId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.users })
    },
  })
}

export function useRetryJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (jobId: string) => adminApi.post(`/jobs/${jobId}/retry`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.jobs })
    },
  })
}

export function useCancelJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (jobId: string) => adminApi.delete(`/jobs/${jobId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.jobs })
    },
  })
}

export function useRevokeToken() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (userId: string) => adminApi.delete(`/oauth/tokens/${userId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.tokens })
    },
  })
}

export function useForceRefreshToken() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (userId: string) => adminApi.post(`/oauth/tokens/${userId}/refresh`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.tokens })
    },
  })
}

export function useInviteAdmin() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (email: string) => adminApi.post('/users/invite', { email }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.users })
    },
  })
}

export function useChangePassword() {
  return useMutation({
    mutationFn: ({ currentPassword, newPassword }: { currentPassword: string; newPassword: string }) =>
      adminApi.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      }),
  })
}