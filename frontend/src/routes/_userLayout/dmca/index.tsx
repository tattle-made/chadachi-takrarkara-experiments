import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import { Search } from "lucide-react"
import { useState } from "react"
import { ProfileFormDialog } from "@/dmca/components/ProfileFormDialog"
import { profileName } from "@/dmca/labels"
import { btnPrimary, cardClass, formatDate, tdClass, thClass } from "@/dmca/ui"
import {
  casesQueryOptions,
  profilesQueryOptions,
} from "@/queries/dmca/profiles.query"
import { currentUserQueryOptions } from "@/queries/user.query"

export const Route = createFileRoute("/_userLayout/dmca/")({
  component: ProfilesPage,
})

/** All profiles, newest first, with a name search and a "Has a case
 * assigned to me" tick. */
function ProfilesPage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState("")
  const { data, isPending, isError } = useQuery({
    ...profilesQueryOptions(query.trim()),
    // keep showing the last results while the next search loads
    placeholderData: keepPreviousData,
  })
  const { data: cases } = useQuery(casesQueryOptions())
  const { data: user } = useQuery(currentUserQueryOptions())
  const [mineOnly, setMineOnly] = useState(false)

  const mine = new Set(
    cases?.data
      .filter((c) => c.assignee?.id === user?.id)
      .map((c) => c.profile.id),
  )
  const profiles = (data?.data ?? []).filter((p) => !mineOnly || mine.has(p.id))

  return (
    <section>
      <div className="mb-4 flex items-center justify-between gap-4">
        <h1 className="text-xl font-semibold text-slate-900">Profiles</h1>
        <div className="flex items-center gap-3">
          <label className="inline-flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={mineOnly}
              onChange={(e) => {
                setMineOnly(e.target.checked)
              }}
            />
            Has a case assigned to me
          </label>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by name"
              className="w-56 rounded-md border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-1 focus:ring-slate-500"
            />
          </div>
          <ProfileFormDialog
            trigger={
              <button type="button" className={btnPrimary}>
                New profile
              </button>
            }
            onSaved={(profile) =>
              navigate({
                to: "/dmca/profiles/$profileId",
                params: { profileId: profile.id },
              })
            }
          />
        </div>
      </div>

      {isPending ? (
        <p className="text-sm text-slate-400">Loading…</p>
      ) : isError ? (
        <p className="text-sm text-red-600">Couldn't load profiles.</p>
      ) : profiles.length === 0 ? (
        <p className="text-sm text-slate-400">
          {mineOnly
            ? "No profiles with a case assigned to you."
            : query.trim()
              ? "No profiles match."
              : "No profiles yet."}
        </p>
      ) : (
        <div className={`overflow-hidden ${cardClass}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className={thClass}>Name</th>
                <th className={thClass}>Created</th>
              </tr>
            </thead>
            <tbody>
              {profiles.map((p) => (
                <tr
                  key={p.id}
                  className="border-b border-slate-100 last:border-0 hover:bg-slate-50"
                >
                  <td className={tdClass}>
                    <Link
                      to="/dmca/profiles/$profileId"
                      params={{ profileId: p.id }}
                      className="font-medium text-slate-900 hover:underline"
                    >
                      {profileName(p)}
                    </Link>
                  </td>
                  <td className={`${tdClass} text-slate-500`}>
                    {formatDate(p.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
