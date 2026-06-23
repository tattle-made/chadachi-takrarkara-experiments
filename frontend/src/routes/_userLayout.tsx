import { useQuery } from "@tanstack/react-query"
import {
  createFileRoute,
  Link,
  Outlet,
  redirect,
  useNavigate,
} from "@tanstack/react-router"
import { Mail, Shield } from "lucide-react"
import apiClient from "@/lib/apiClient"
import { useLogoutMutation } from "@/queries/auth.query"
import { currentUserQueryOptions } from "@/queries/user.query"
import useAuthStore from "@/stores/authStore"

export const Route = createFileRoute("/_userLayout")({
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
  },
  component: UserLayout,
})

const TOOL_LINKS = [
  { to: "/emailGeneration", label: "Write Email", icon: Mail },
] as const

function UserLayout() {
  const navigate = useNavigate()
  const { mutate: logout } = useLogoutMutation()
  const { data: user } = useQuery(currentUserQueryOptions())
  const isAdmin = user?.role === "admin"

  const handleLogout = () => {
    logout(undefined, { onSettled: () => navigate({ to: "/login" }) })
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white px-6 py-3 flex items-center justify-between">
        <nav className="flex items-center gap-1">
          <span className="mr-4 font-semibold text-slate-900">Takrarkara</span>
          {isAdmin && (
            <Link
              to="/admin"
              className="inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 hover:text-slate-900 [&.active]:bg-slate-100 [&.active]:font-medium [&.active]:text-slate-900"
            >
              <Shield className="size-4" />
              Admin
            </Link>
          )}
          {TOOL_LINKS.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className="inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 hover:text-slate-900 [&.active]:bg-slate-100 [&.active]:font-medium [&.active]:text-slate-900"
            >
              <Icon className="size-4" />
              {label}
            </Link>
          ))}
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
