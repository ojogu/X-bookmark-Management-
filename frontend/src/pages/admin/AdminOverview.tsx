import { Users, Bookmark, Clock, Zap, Database, Rabbit } from 'lucide-react'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { StatCard } from '@/components/admin/StatCard'
import { Spinner } from '@/components/ui/spinner'
import { Badge } from '@/components/ui/badge'
import { useStatsOverview, useSignups, useBookmarks, useHealthMetrics } from '@/features/admin/hooks'

export default function AdminOverview() {
  const { data: stats, isLoading: statsLoading } = useStatsOverview()
  const { data: signups, isLoading: signupsLoading } = useSignups('30d')
  const { data: bookmarks, isLoading: bookmarksLoading } = useBookmarks('14d')
  const { data: health, isLoading: healthLoading } = useHealthMetrics()

  if (statsLoading || signupsLoading || bookmarksLoading || healthLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner className="size-8" />
      </div>
    )
  }

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
    return num.toString()
  }

  const redisPercent = health?.redis_memory_total_mb 
    ? Math.round((health.redis_memory_used_mb / health.redis_memory_total_mb) * 100) 
    : 0

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Users"
          value={formatNumber(stats?.total_users ?? 0)}
          subtitle={`+${stats?.total_users_daily ?? 0} today`}
          icon={Users}
        />
        <StatCard
          title="Active Users"
          value={formatNumber(stats?.active_users ?? 0)}
          subtitle={`${stats?.active_users_daily ?? 0} today`}
          icon={Users}
        />
        <StatCard
          title="Bookmarks Today"
          value={formatNumber(stats?.bookmarks_today ?? 0)}
          subtitle={`${stats?.bookmarks_weekly ?? 0} this week`}
          icon={Bookmark}
        />
        <StatCard
          title="Sync Jobs Today"
          value={formatNumber(stats?.jobs_today ?? 0)}
          subtitle={`${stats?.jobs_weekly ?? 0} this week`}
          icon={Clock}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Signups Chart */}
        <div className="flex flex-col gap-2 rounded-lg border border-border/60 bg-card p-4">
          <h3 className="text-sm font-medium text-muted-foreground">Signups (Last 30 Days)</h3>
          <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={signups ?? []}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis 
                  dataKey="date" 
                  tick={{ fontSize: 10 }} 
                  tickFormatter={(value) => value.slice(5)}
                  stroke="hsl(var(--muted-foreground))"
                />
                <YAxis tick={{ fontSize: 10 }} stroke="hsl(var(--muted-foreground))" />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--card))', 
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px'
                  }}
                />
                <Line 
                  type="monotone" 
                  dataKey="count" 
                  stroke="hsl(var(--primary))" 
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Bookmarks Chart */}
        <div className="flex flex-col gap-2 rounded-lg border border-border/60 bg-card p-4">
          <h3 className="text-sm font-medium text-muted-foreground">Bookmarks (Last 14 Days)</h3>
          <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={bookmarks ?? []}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis 
                  dataKey="date" 
                  tick={{ fontSize: 10 }}
                  tickFormatter={(value) => value.slice(5)}
                  stroke="hsl(var(--muted-foreground))"
                />
                <YAxis tick={{ fontSize: 10 }} stroke="hsl(var(--muted-foreground))" />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--card))', 
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px'
                  }}
                />
                <Bar 
                  dataKey="count" 
                  fill="hsl(var(--primary))" 
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* System Status Strip */}
      <div className="flex flex-col gap-2 rounded-lg border border-border/60 bg-card p-4">
        <h3 className="text-sm font-medium text-muted-foreground">System Status</h3>
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center gap-2">
            <Badge variant="default" className="bg-emerald-500/20 text-emerald-500">
              <Zap className="mr-1 size-3" />
              API
            </Badge>
            <span className="text-sm text-muted-foreground">Online</span>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="default" className={health?.celery_workers ? "bg-emerald-500/20 text-emerald-500" : "bg-amber-500/20 text-amber-500"}>
              <Clock className="mr-1 size-3" />
              Celery
            </Badge>
            <span className="text-sm text-muted-foreground">
              {health?.celery_workers ?? 0} workers
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="default" className={redisPercent < 80 ? "bg-emerald-500/20 text-emerald-500" : "bg-amber-500/20 text-amber-500"}>
              <Database className="mr-1 size-3" />
              Redis
            </Badge>
            <span className="text-sm text-muted-foreground">
              {redisPercent}% used
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="default" className="bg-emerald-500/20 text-emerald-500">
              <Rabbit className="mr-1 size-3" />
              RabbitMQ
            </Badge>
            <span className="text-sm text-muted-foreground">
              {health?.rabbitmq_queue_depth ?? 0} queued
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}