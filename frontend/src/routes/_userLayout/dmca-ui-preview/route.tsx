import { createFileRoute, Link, Outlet, redirect } from "@tanstack/react-router"
import { Inbox, Settings, Users } from "lucide-react"
import apiClient from "@/lib/apiClient"
import { usePreviewStore } from "@/preview/store"

// UI-only preview of the DMCA takedown flow: dummy data + React state, no
// backend calls apart from the existing admin check. Not linked in the nav.
export const Route = createFileRoute("/_userLayout/dmca-ui-preview")({
  beforeLoad: async () => {
    try {
      const response = await apiClient.get("/api/v1/users/me")
      if (response.data.role !== "admin") {
        throw redirect({ to: "/" })
      }
    } catch (err) {
      if (err instanceof Error && "isRedirect" in err) throw err
      throw redirect({ to: "/" })
    }
  },
  component: PreviewLayout,
})

const NAV_LINK =
  "inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm text-slate-600 hover:bg-white hover:text-slate-900 [&.active]:bg-white [&.active]:font-medium [&.active]:text-slate-900 [&.active]:shadow-sm"

function PreviewLayout() {
  const draftCount = usePreviewStore(
    (s) => s.emails.filter((e) => e.status === "draft").length,
  )
  const resetDemo = usePreviewStore((s) => s.resetDemo)

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-slate-100 px-3 py-2">
        <div className="flex items-center gap-1">
          <span className="mr-2 text-sm font-semibold text-slate-900">
            DMCA takedowns
          </span>
          <Link
            to="/dmca-ui-preview"
            activeOptions={{ exact: true }}
            className={NAV_LINK}
          >
            <Users className="size-4" />
            Profiles
          </Link>
          <Link to="/dmca-ui-preview/outbox" className={NAV_LINK}>
            <Inbox className="size-4" />
            Outbox
            {draftCount > 0 && (
              <span className="rounded-full bg-slate-900 px-1.5 text-xs text-white">
                {draftCount}
              </span>
            )}
          </Link>
          <Link to="/dmca-ui-preview/config" className={NAV_LINK}>
            <Settings className="size-4" />
            Config
          </Link>
        </div>
        <div className="flex items-center gap-3">
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
            UI preview · dummy data
          </span>
          <button
            type="button"
            onClick={resetDemo}
            className="text-xs text-slate-500 underline underline-offset-2 hover:text-slate-900"
          >
            Reset demo data
          </button>
        </div>
      </div>
      <Outlet />
    </div>
  )
}
