import {
  createFileRoute,
  Link,
  Outlet,
  redirect,
  useNavigate,
} from "@tanstack/react-router"
import apiClient from "@/lib/apiClient"
import { useLogoutMutation } from "@/queries/auth.query"
import useAuthStore from "@/stores/authStore"

export const Route = createFileRoute("/_layout")({
  beforeLoad: async () => {
    const { accessToken, setAccessToken } = useAuthStore.getState()
    if (!accessToken) {
      try {
        const response = await apiClient.post("/api/v1/auth/refresh")
        setAccessToken(response.data.access_token)
      } catch {
        throw redirect({ to: "/login" })
      }
    }
    const response = await apiClient.get("/api/v1/users/me")
    if (response.data.role !== "admin") {
      throw redirect({ to: "/" })
    }
  },
  component: AdminLayout,
})

function AdminLayout() {
  const navigate = useNavigate()
  const { mutate: logout } = useLogoutMutation()

  const handleLogout = () => {
    logout(undefined, { onSettled: () => navigate({ to: "/login" }) })
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white px-6 py-3 flex items-center justify-between">
        <nav className="flex items-center gap-6">
          <span className="font-semibold text-slate-900">Admin</span>
          <Link
            to="/admin"
            className="text-sm text-slate-600 hover:text-slate-900 [&.active]:font-medium [&.active]:text-slate-900"
          >
            Users
          </Link>
        </nav>
        <button
          type="button"
          onClick={handleLogout}
          className="text-sm text-slate-500 hover:text-slate-900"
        >
          Sign out
        </button>
      </header>
      <main className="mx-auto max-w-5xl p-6">
        <Outlet />
      </main>
    </div>
  )
}
