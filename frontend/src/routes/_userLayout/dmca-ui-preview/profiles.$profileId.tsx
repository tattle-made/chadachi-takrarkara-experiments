import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft, Plus } from "lucide-react"
import { DocumentsPanel } from "@/preview/components/DocumentsPanel"
import { EmailList } from "@/preview/components/EmailList"
import {
  btnPrimary,
  cardClass,
  formatDate,
  tdClass,
  thClass,
} from "@/preview/components/ui"
import { usePreviewStore } from "@/preview/store"

export const Route = createFileRoute(
  "/_userLayout/dmca-ui-preview/profiles/$profileId",
)({
  component: ProfilePage,
})

function ProfilePage() {
  const { profileId } = Route.useParams()
  const state = usePreviewStore()
  const profile = state.profiles.find((p) => p.id === profileId)

  if (!profile) {
    return (
      <p className="text-sm text-slate-500">
        Profile not found.{" "}
        <Link to="/dmca-ui-preview" className="underline">
          Back to profiles
        </Link>
      </p>
    )
  }

  const cases = state.cases.filter((c) => c.profileId === profile.id)
  const caseIds = cases.map((c) => c.id)
  const emails = state.emails.filter((e) => caseIds.includes(e.caseId))

  return (
    <div className="space-y-10">
      <div>
        <Link
          to="/dmca-ui-preview"
          className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900"
        >
          <ArrowLeft className="size-4" />
          Profiles
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">
              {profile.fullName}
            </h1>
            <p className="mt-0.5 text-sm text-slate-500">
              Created {formatDate(profile.createdAt)}
            </p>
            {profile.notes && (
              <p className="mt-2 text-sm text-slate-600">{profile.notes}</p>
            )}
          </div>
          <Link
            to="/dmca-ui-preview/cases/new"
            search={{ profileId: profile.id }}
            className={`${btnPrimary} inline-flex items-center gap-2`}
          >
            <Plus className="size-4" />
            New case
          </Link>
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
        {cases.length === 0 ? (
          <p className="text-sm text-slate-400">
            No cases yet. Create one to start drafting takedown emails.
          </p>
        ) : (
          <div className={`overflow-hidden ${cardClass}`}>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className={thClass}>Case</th>
                  <th className={thClass}>Links</th>
                  <th className={thClass}>Emails</th>
                  <th className={thClass}>Created</th>
                </tr>
              </thead>
              <tbody>
                {cases.map((c) => {
                  const caseEmails = emails.filter((e) => e.caseId === c.id)
                  const sent = caseEmails.filter(
                    (e) => e.status === "sent",
                  ).length
                  return (
                    <tr
                      key={c.id}
                      className="border-b border-slate-100 last:border-0 hover:bg-slate-50"
                    >
                      <td className={tdClass}>
                        <Link
                          to="/dmca-ui-preview/cases/$caseId"
                          params={{ caseId: c.id }}
                          className="font-medium text-slate-900 hover:underline"
                        >
                          {c.title}
                        </Link>
                      </td>
                      <td className={`${tdClass} text-slate-700`}>
                        {state.links.filter((l) => l.caseId === c.id).length}
                      </td>
                      <td className={`${tdClass} text-slate-500`}>
                        {sent} of {caseEmails.length} sent
                      </td>
                      <td className={`${tdClass} text-slate-500`}>
                        {formatDate(c.createdAt)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-base font-semibold text-slate-900">
          All emails for {profile.fullName}
        </h2>
        <EmailList emails={emails} showCase emptyText="No emails yet." />
      </section>
    </div>
  )
}
