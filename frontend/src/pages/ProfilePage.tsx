import { MapPin, Users, UserCheck, MessageSquare, ExternalLink } from 'lucide-react'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { useProfile } from '@/features/bookmarks/hooks'
import { useAuth } from '@/hooks/useAuth'
import { formatCount } from '@/lib/utils'

export default function ProfilePage() {
  const { data: profile, isLoading } = useProfile()
  const { logout } = useAuth()

  return (
    <div className="flex h-full flex-col">
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border-subtle px-4 sm:px-6">
        <SidebarTrigger className="text-text-muted hover:text-text-primary" />
        <h1 className="font-serif italic text-lg text-text-primary">Profile</h1>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-8 sm:px-6">
        <div className="mx-auto max-w-lg">
          {isLoading && (
            <div className="flex flex-col gap-6">
              <div className="flex items-center gap-4">
                <Skeleton className="h-20 w-20 rounded-full" />
                <div className="flex flex-col gap-2">
                  <Skeleton className="h-5 w-40 rounded" />
                  <Skeleton className="h-4 w-28 rounded" />
                </div>
              </div>
              <Skeleton className="h-16 w-full rounded-xl" />
              <Skeleton className="h-12 w-full rounded-xl" />
            </div>
          )}

          {profile && (
            <div className="flex flex-col gap-6">
              {/* Profile card */}
              <div className="rounded-2xl border border-border-subtle bg-bg-card p-6">
                {/* Avatar + name */}
                <div className="mb-5 flex items-center gap-4">
                  <Avatar className="h-20 w-20">
                    <AvatarImage src={profile.profile_image_url ?? undefined} alt={profile.name} />
                    <AvatarFallback className="bg-brand-light text-2xl font-medium text-brand-mid">
                      {profile.name.slice(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-xl font-semibold text-text-primary">{profile.name}</h2>
                      {profile.verified && (
                        <span className="text-brand-mid text-sm">✓</span>
                      )}
                    </div>
                    <p className="text-sm text-text-muted">@{profile.username}</p>
                    <a
                      href={`https://x.com/${profile.username}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-1.5 flex items-center gap-1 text-xs text-brand-mid transition-opacity hover:opacity-75"
                    >
                      View on X
                      <ExternalLink size={10} />
                    </a>
                  </div>
                </div>

                {/* Bio */}
                {profile.description && (
                  <>
                    <p className="mb-5 text-sm leading-relaxed text-text-secondary">
                      {profile.description}
                    </p>
                    <Separator className="mb-5" />
                  </>
                )}

                {/* Location */}
                {profile.location && (
                  <div className="mb-5 flex items-center gap-2 text-sm text-text-muted">
                    <MapPin size={13} />
                    {profile.location}
                  </div>
                )}

                {/* Stats */}
                <div className="flex gap-6">
                  <div className="flex flex-col items-center gap-0.5">
                    <span className="text-lg font-semibold text-text-primary">
                      {formatCount(profile.followers_count)}
                    </span>
                    <span className="flex items-center gap-1 text-xs text-text-muted">
                      <Users size={10} />
                      Followers
                    </span>
                  </div>
                  <div className="flex flex-col items-center gap-0.5">
                    <span className="text-lg font-semibold text-text-primary">
                      {formatCount(profile.following_count)}
                    </span>
                    <span className="flex items-center gap-1 text-xs text-text-muted">
                      <UserCheck size={10} />
                      Following
                    </span>
                  </div>
                  <div className="flex flex-col items-center gap-0.5">
                    <span className="text-lg font-semibold text-text-primary">
                      {formatCount(profile.tweet_count)}
                    </span>
                    <span className="flex items-center gap-1 text-xs text-text-muted">
                      <MessageSquare size={10} />
                      Posts
                    </span>
                  </div>
                </div>
              </div>

              {/* Sign out */}
              <div className="rounded-2xl border border-border-subtle bg-bg-card p-6">
                <h3 className="mb-1 text-sm font-medium text-text-primary">Account</h3>
                <p className="mb-4 text-xs text-text-muted">
                  Signing out will clear your session. Your bookmarks stay synced.
                </p>
                <Button
                  variant="outline"
                  onClick={logout}
                  className="border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive"
                >
                  Sign out
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
