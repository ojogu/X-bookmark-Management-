import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { TooltipProvider } from '@/components/ui/tooltip'
import LandingPage from '@/pages/LandingPage'
import CallbackPage from '@/pages/CallbackPage'
import Error500Page from '@/pages/Error500Page'
import Error404Page from '@/pages/Error404Page'
import ProtectedRoute from '@/router/ProtectedRoute'
import AppLayout from '@/components/app/AppLayout'
import BookmarksPage from '@/pages/BookmarksPage'
import UnreadPage from '@/pages/UnreadPage'
import FoldersPage from '@/pages/FoldersPage'
import FolderPage from '@/pages/FolderPage'
import TagsPage from '@/pages/TagsPage'
import TagPage from '@/pages/TagPage'
import ProfilePage from '@/pages/ProfilePage'
import AdminOverview from '@/pages/admin/AdminOverview'
import AdminLoginPage from '@/pages/admin/AdminLoginPage'
import AdminProtectedRoute from '@/router/AdminProtectedRoute'

export default function Router() {
  return (
    <TooltipProvider>
      <BrowserRouter>
        <Routes>
        {/* Public */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/callback" element={<CallbackPage />} />
        <Route path="/error/500" element={<Error500Page />} />
        <Route path="/error/404" element={<Error404Page />} />

        {/* Authenticated app — shared sidebar layout */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<BookmarksPage />} />
          <Route path="unread" element={<UnreadPage />} />
          <Route path="folders" element={<FoldersPage />} />
          <Route path="folders/:id" element={<FolderPage />} />
          <Route path="tags" element={<TagsPage />} />
          <Route path="tags/:name" element={<TagPage />} />
          <Route path="profile" element={<ProfilePage />} />
        </Route>

        {/* Admin routes */}
        <Route path="/admin/login" element={<AdminLoginPage />} />
        <Route
          path="/admin"
          element={
            <AdminProtectedRoute>
              <AppLayout />
            </AdminProtectedRoute>
          }
        >
          <Route index element={<AdminOverview />} />
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Error404Page />} />
      </Routes>
      </BrowserRouter>
    </TooltipProvider>
  )
}
