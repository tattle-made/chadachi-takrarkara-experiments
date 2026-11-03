import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft, Plus } from "lucide-react"
import { useState } from "react"
import { AddLinksFlow } from "@/preview/components/AddLinksFlow"
import { ProfileDocsNote } from "@/preview/components/DocumentsPanel"
import { EmailList } from "@/preview/components/EmailList"
import { btnSecondary, cardClass, formatDate } from "@/preview/components/ui"
import { usePreviewStore } from "@/preview/store"

export const Route = createFileRoute(
  "/_userLayout/dmca-ui-preview/cases/$caseId",
)({
  component: CasePage,
})

function CasePage() {
  const { caseId } = Route.useParams()
  const state = usePreviewStore()
  const [addingLinks, setAddingLinks] = useState(false)

  const caseItem = state.cases.find((c) => c.id === caseId)
  const profile = state.profiles.find((p) => p.id === caseItem?.profileId)

  if (!caseItem || !profile) {
    return (
      <p className="text-sm text-slate-500">
        Case not found.{" "}
        <Link to="/dmca-ui-preview" className="underline">
          Back to profiles
        </Link>
      </p>
    )
  }

  const emails = state.emails.filter((e) => e.caseId === caseId)
  const linkCount = state.links.filter((l) => l.caseId === caseId).length

  return (
    <div className="space-y-8">
      <div>
        <Link
          to="/dmca-ui-preview/profiles/$profileId"
          params={{ profileId: profile.id }}
          className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900"
        >
          <ArrowLeft className="size-4" />
          {profile.fullName}
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">
              {caseItem.title}
            </h1>
            <p className="mt-0.5 text-sm text-slate-500">
              {linkCount} {linkCount === 1 ? "link" : "links"} · {emails.length}{" "}
              {emails.length === 1 ? "email" : "emails"} · created{" "}
              {formatDate(caseItem.createdAt)}
            </p>
            <div className="mt-2">
              <ProfileDocsNote profileId={profile.id} />
            </div>
          </div>
          {!addingLinks && (
            <button
              type="button"
              onClick={() => setAddingLinks(true)}
              className={`${btnSecondary} inline-flex items-center gap-2`}
            >
              <Plus className="size-4" />
              Add more links
            </button>
          )}
        </div>
      </div>

      {addingLinks && (
        <section className={`${cardClass} p-6`}>
          <h2 className="mb-4 text-sm font-semibold text-slate-900">
            Add more links
          </h2>
          <AddLinksFlow
            caseId={caseId}
            onDone={() => setAddingLinks(false)}
            onCancel={() => setAddingLinks(false)}
          />
        </section>
      )}

      <section>
        <h2 className="mb-1 text-base font-semibold text-slate-900">Emails</h2>
        <p className="mb-3 text-sm text-slate-500">
          One email per recipient. Open a draft to check or edit it, then select
          and send one or many.
        </p>
        <EmailList
          emails={emails}
          emptyText="No emails yet. Add links to create drafts."
        />
      </section>
    </div>
  )
}
