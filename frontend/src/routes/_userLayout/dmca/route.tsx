import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link, Outlet } from "@tanstack/react-router"
import { Inbox, Settings, Users } from "lucide-react"
import { emailsQueryOptions } from "@/queries/dmca/emails.query"
import { currentUserQueryOptions } from "@/queries/user.query"

// DMCA takedowns: profiles and their cases, the outbox, and (admins) Config.
export const Route = createFileRoute("/_userLayout/dmca")({
  component: DmcaLayout,
})

const NAV_LINK =
  "inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm text-slate-600 hover:bg-white hover:text-slate-900 [&.active]:bg-white [&.active]:font-medium [&.active]:text-slate-900 [&.active]:shadow-sm"

function DmcaLayout() {
  const { data: user } = useQuery(currentUserQueryOptions())
  const { data: drafts } = useQuery(emailsQueryOptions({ status: "draft" }))
  const draftCount = drafts?.length ?? 0

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-1 rounded-lg bg-slate-100 px-3 py-2">
        <span className="mr-2 text-sm font-semibold text-slate-900">
          DMCA takedowns
        </span>
        <Link to="/dmca" activeOptions={{ exact: true }} className={NAV_LINK}>
          <Users className="size-4" />
          Profiles
        </Link>
        <Link to="/dmca/outbox" className={NAV_LINK}>
          <Inbox className="size-4" />
          Outbox
          {draftCount > 0 && (
            <span className="rounded-full bg-slate-900 px-1.5 text-xs text-white">
              {draftCount}
            </span>
          )}
        </Link>
        {user?.role === "admin" && (
          <Link to="/dmca/config" className={NAV_LINK}>
            <Settings className="size-4" />
            Config
          </Link>
        )}
      </div>
      <Outlet />
    </div>
  )
}
