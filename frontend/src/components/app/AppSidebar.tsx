import { Link, NavLink, useLocation } from 'react-router-dom'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarSeparator,
} from '@/components/ui/sidebar'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import {
  Bookmark,
  BookmarkCheck,
  ChevronRight,
  Folder,
  FolderOpen,
  LogOut,
  Tag,
  User,
} from 'lucide-react'
import { useProfile, useFolders, useUnreadBookmarks } from '@/features/bookmarks/hooks'
import { useAuth } from '@/hooks/useAuth'

export default function AppSidebar() {
  const location = useLocation()
  const { logout } = useAuth()
  const { data: profile } = useProfile()
  const { data: folders } = useFolders()
  const { data: unread } = useUnreadBookmarks()

  const unreadCount = unread?.data?.length ?? 0

  const isActive = (path: string, exact = false) =>
    exact ? location.pathname === path : location.pathname.startsWith(path)

  return (
    <Sidebar collapsible="offcanvas">
      {/* Logo */}
      <SidebarHeader className="border-b border-sidebar-border px-4 py-4">
        <Link to="/" className="font-serif italic text-xl text-sidebar-foreground">
          Save<span className="text-brand-mid">Stack</span>
        </Link>
      </SidebarHeader>

      <SidebarContent>
        {/* User section */}
        {profile && (
          <>
            <div className="px-4 py-3">
              <NavLink
                to="/dashboard/profile"
                className="flex items-center gap-3 rounded-lg p-2 transition-colors hover:bg-sidebar-accent"
              >
                <Avatar className="h-8 w-8 shrink-0">
                  <AvatarImage src={profile.profile_image_url ?? undefined} alt={profile.name} />
                  <AvatarFallback className="bg-brand-light text-xs font-medium text-brand-mid">
                    {profile.name.slice(0, 2).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-sidebar-foreground">
                    {profile.name}
                  </p>
                  <p className="truncate text-xs text-text-muted">@{profile.username}</p>
                </div>
              </NavLink>
            </div>
            <SidebarSeparator />
          </>
        )}

        {/* Navigation */}
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {/* All Bookmarks */}
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={isActive('/dashboard', true)}
                  tooltip="All Bookmarks"
                >
                  <NavLink to="/dashboard" end>
                    <Bookmark size={16} />
                    <span>All Bookmarks</span>
                  </NavLink>
                </SidebarMenuButton>
              </SidebarMenuItem>

              {/* Unread */}
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={isActive('/dashboard/unread')}
                  tooltip="Unread"
                >
                  <NavLink to="/dashboard/unread">
                    <BookmarkCheck size={16} />
                    <span>Unread</span>
                  </NavLink>
                </SidebarMenuButton>
                {unreadCount > 0 && (
                  <SidebarMenuBadge className="bg-brand-light text-brand-mid">
                    {unreadCount}
                  </SidebarMenuBadge>
                )}
              </SidebarMenuItem>

              {/* Folders — collapsible */}
              <Collapsible defaultOpen={isActive('/dashboard/folders')}>
                <SidebarMenuItem>
                  <CollapsibleTrigger asChild>
                    <SidebarMenuButton
                      isActive={isActive('/dashboard/folders')}
                      tooltip="Folders"
                    >
                      {isActive('/dashboard/folders') ? (
                        <FolderOpen size={16} />
                      ) : (
                        <Folder size={16} />
                      )}
                      <span>Folders</span>
                      <ChevronRight
                        size={14}
                        className="ml-auto transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90"
                      />
                    </SidebarMenuButton>
                  </CollapsibleTrigger>
                </SidebarMenuItem>

                <CollapsibleContent>
                  <SidebarMenuSub>
                    {folders && folders.length > 0 ? (
                      folders.map((folder: { id: string; name: string; bookmarkCount: number }) => (
                        <SidebarMenuSubItem key={folder.id}>
                          <SidebarMenuSubButton
                            asChild
                            isActive={location.pathname === `/dashboard/folders/${folder.id}`}
                          >
                            <NavLink to={`/dashboard/folders/${folder.id}`}>
                              <span className="flex-1 truncate">{folder.name}</span>
                              <span className="text-xs text-text-muted">{folder.bookmarkCount}</span>
                            </NavLink>
                          </SidebarMenuSubButton>
                        </SidebarMenuSubItem>
                      ))
                    ) : (
                      <SidebarMenuSubItem>
                        <SidebarMenuSubButton asChild>
                          <NavLink to="/dashboard/folders">
                            <span className="text-text-muted">Manage folders</span>
                          </NavLink>
                        </SidebarMenuSubButton>
                      </SidebarMenuSubItem>
                    )}
                  </SidebarMenuSub>
                </CollapsibleContent>
              </Collapsible>

              {/* Tags */}
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={isActive('/dashboard/tags')}
                  tooltip="Tags"
                >
                  <NavLink to="/dashboard/tags">
                    <Tag size={16} />
                    <span>Tags</span>
                  </NavLink>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      {/* Footer */}
      <SidebarFooter className="border-t border-sidebar-border p-3">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              asChild
              isActive={isActive('/dashboard/profile')}
              tooltip="Profile"
            >
              <NavLink to="/dashboard/profile">
                <User size={16} />
                <span>Profile</span>
              </NavLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton onClick={logout} tooltip="Sign out">
              <LogOut size={16} />
              <span>Sign out</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}
