import { cn } from '@/lib/utils'
import { LucideIcon } from 'lucide-react'

interface StatCardProps {
  title: string
  value: number | string
  subtitle?: string
  trend?: {
    value: number
    label: string
  }
  icon?: LucideIcon
  className?: string
}

export function StatCard({ title, value, subtitle, trend, icon: Icon, className }: StatCardProps) {
  return (
    <div
      className={cn(
        'flex flex-col gap-1.5 rounded-lg border border-border/60 bg-card p-4',
        className
      )}
    >
      <span className="text-sm font-medium text-muted-foreground">{title}</span>
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-semibold tracking-tight">{value}</span>
        {Icon && (
          <Icon className="size-5 text-muted-foreground" />
        )}
      </div>
      {subtitle && (
        <span className="text-sm text-muted-foreground">{subtitle}</span>
      )}
      {trend && (
        <div className={cn(
          'flex items-center gap-1 text-xs',
          trend.value >= 0 ? 'text-emerald-500' : 'text-destructive'
        )}>
          <span>{trend.value >= 0 ? '+' : ''}{trend.value}%</span>
          <span className="text-muted-foreground">{trend.label}</span>
        </div>
      )}
    </div>
  )
}