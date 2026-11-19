import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft, Plus } from "lucide-react"
import { DocumentsPanel } from "@/dmca/components/DocumentsPanel"
import { ProfileFormDialog } from "@/dmca/components/ProfileFormDialog"
import {
  btnPrimary,
  btnSecondary,
  cardClass,
  formatDate,
  tdClass,
  thClass,
} from "@/dmca/ui"
import { profileQueryOptions } from "@/queries/dmca/profiles.query"

export const Route = createFileRoute("/_userLayout/dmca/profiles/$profileId")({
  component: ProfilePage,
})

/** One person: their details, documents and cases. */
function ProfilePage() {
  const { profileId } = Route.useParams()
  const { data: profile, isPending } = useQuery(profileQueryOptions(profileId))

  if (isPending) return <p className="text-sm text-slate-400">Loading…</p>
  if (!profile) {
    return (
      <p className="text-sm text-slate-500">
        Profile not found.{" "}
        <Link to="/dmca" className="underline">
          Back to profiles
        </Link>
      </p>
    )
  }

  return (
    <div className="space-y-10">
      <div>
        <Link
          to="/dmca"
          className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900"
        >
          <ArrowLeft className="size-4" />
          Profiles
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">
              {profile.full_name}
            </h1>
            <p className="mt-0.5 text-sm text-slate-500">
              {profile.display_name && <>Shown as {profile.display_name} · </>}
              Created {formatDate(profile.created_at)}
            </p>
            {profile.notes && (
              <p className="mt-2 whitespace-pre-line text-sm text-slate-600">
                {profile.notes}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <ProfileFormDialog
              profile={profile}
              trigger={
                <button type="button" className={btnSecondary}>
                  Edit
                </button>
              }
            />
            <Link
              to="/dmca/cases/new"
              search={{ profileId: profile.id }}
              className={`${btnPrimary} inline-flex items-center gap-2`}
            >
              <Plus className="size-4" />
              New case
            </Link>
          </div>
        </div>
      </div>

      <section>
        <h2 className="mb-3 text-base font-semibold text-slate-900">
          Documents
        </h2>
        <DocumentsPanel profileId={profile.id} />
      </section>

      <section>
        <h2 className="mb-3 text-base font-semibold text-slate-900">Cases</h2>
        {profile.cases.length === 0 ? (
          <p className="text-sm text-slate-400">
            No cases yet. Create one to start drafting takedown emails.
          </p>
        ) : (
          <div className={`overflow-hidden ${cardClass}`}>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className={thClass}>Case</th>
                  <th className={thClass}>Assigned to</th>
                  <th className={thClass}>Created</th>
                </tr>
              </thead>
              <tbody>
                {profile.cases.map((c) => (
                  <tr
                    key={c.id}
                    className="border-b border-slate-100 last:border-0 hover:bg-slate-50"
                  >
                    <td className={tdClass}>
                      <Link
                        to="/dmca/cases/$caseId"
                        params={{ caseId: c.id }}
                        className="font-medium text-slate-900 hover:underline"
                      >
                        {c.title}
                      </Link>
                      {c.is_minor && (
                        <span className="ml-2 rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-800">
                          Minor
                        </span>
                      )}
                    </td>
                    <td className={`${tdClass} text-slate-500`}>
                      {c.assignee?.email ?? "–"}
                    </td>
                    <td className={`${tdClass} text-slate-500`}>
                      {formatDate(c.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
