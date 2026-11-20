import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { useEffect, useState } from "react"
import { AddLinksFlow } from "@/dmca/components/AddLinksFlow"
import { CaseLinks } from "@/dmca/components/CaseLinks"
import { ProfileDocsNote } from "@/dmca/components/DocumentsPanel"
import { EmailList } from "@/dmca/components/EmailList"
import {
  EscalationReview,
  ReviewDrafts,
  type ReviewSeed,
  seedsFromLinks,
} from "@/dmca/components/ReviewDrafts"
import type { CaseDetail } from "@/dmca/types"
import { cardClass, fieldBase, formatDate } from "@/dmca/ui"
import { emailsQueryOptions } from "@/queries/dmca/emails.query"
import {
  assigneesQueryOptions,
  caseQueryOptions,
  useUpdateCase,
} from "@/queries/dmca/profiles.query"

export const Route = createFileRoute("/_userLayout/dmca/cases/$caseId")({
  // ?escalate=<email id> opens the review pre-filled for escalating that email
  validateSearch: (search: Record<string, unknown>): { escalate?: string } => ({
    escalate: typeof search.escalate === "string" ? search.escalate : undefined,
  }),
  component: CasePage,
})

// what's open under the links: nothing, the paste box, or a review
type Panel = null | { kind: "add" } | { kind: "review"; seeds: ReviewSeed[] }

/** One case: its links, adding more, reviewing who to email, and its emails. */
function CasePage() {
  const { caseId } = Route.useParams()
  const { escalate } = Route.useSearch()
  const navigate = Route.useNavigate()
  const { data: caseItem, isPending } = useQuery(caseQueryOptions(caseId))
  const { data: emails = [] } = useQuery(
    emailsQueryOptions({ case_id: caseId }),
  )
  const [panel, setPanel] = useState<Panel>(null)

  // Escalate from lower down this page only changes the URL, so bring the
  // review into view
  useEffect(() => {
    if (escalate) window.scrollTo({ top: 0, behavior: "smooth" })
  }, [escalate])

  if (isPending) return <p className="text-sm text-slate-400">Loading…</p>
  if (!caseItem) {
    return (
      <p className="text-sm text-slate-500">
        Case not found.{" "}
        <Link to="/dmca" className="underline">
          Back to profiles
        </Link>
      </p>
    )
  }

  const closeEscalation = () => navigate({ search: {} })

  return (
    <div className="space-y-8">
      <CaseHeader
        caseItem={caseItem}
        emailCount={emails.length}
        noReplyCount={emails.filter((e) => e.no_reply_48h).length}
      />

      {escalate ? (
        <section className={`${cardClass} p-6`}>
          <h2 className="mb-4 text-sm font-semibold text-slate-900">
            Escalate
          </h2>
          <EscalationReview
            emailId={escalate}
            caseItem={caseItem}
            emails={emails}
            onDone={closeEscalation}
            onCancel={closeEscalation}
          />
        </section>
      ) : panel ? (
        <section className={`${cardClass} p-6`}>
          <h2 className="mb-4 text-sm font-semibold text-slate-900">
            {panel.kind === "add" ? "Add links" : "Who to email"}
          </h2>
          {panel.kind === "add" ? (
            <AddLinksFlow
              caseItem={caseItem}
              emails={emails}
              onClose={() => setPanel(null)}
            />
          ) : (
            <ReviewDrafts
              caseItem={caseItem}
              emails={emails}
              seeds={panel.seeds}
              onDone={() => setPanel(null)}
              onCancel={() => setPanel(null)}
            />
          )}
        </section>
      ) : null}

      <CaseLinks
        caseItem={caseItem}
        emails={emails}
        onAdd={() => setPanel({ kind: "add" })}
        onDraft={(links) =>
          setPanel({ kind: "review", seeds: seedsFromLinks(links) })
        }
      />

      <section>
        <h2 className="mb-3 text-base font-semibold text-slate-900">Emails</h2>
        <EmailList
          emails={emails}
          emptyText="No emails yet. Add links to create drafts."
        />
      </section>
    </div>
  )
}

/** Back link, title, minor badge, who it's assigned to, and the docs note. */
function CaseHeader({
  caseItem,
  emailCount,
  noReplyCount,
}: {
  caseItem: CaseDetail
  emailCount: number
  // sent emails with no reply after 48 hours
  noReplyCount: number
}) {
  const { data: assignees = [] } = useQuery(assigneesQueryOptions())
  const updateCase = useUpdateCase(caseItem.id)

  return (
    <div>
      <Link
        to="/dmca/profiles/$profileId"
        params={{ profileId: caseItem.profile.id }}
        className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900"
      >
        <ArrowLeft className="size-4" />
        {caseItem.profile.full_name}
      </Link>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold text-slate-900">
            {caseItem.title}
            {caseItem.is_minor && (
              <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-800">
                Minor
              </span>
            )}
          </h1>
          <p className="mt-0.5 text-sm text-slate-500">
            {caseItem.links.length}{" "}
            {caseItem.links.length === 1 ? "link" : "links"} · {emailCount}{" "}
            {emailCount === 1 ? "email" : "emails"} · created{" "}
            {formatDate(caseItem.created_at)}
            {noReplyCount > 0 && (
              <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                {noReplyCount} no reply · 48h+
              </span>
            )}
          </p>
          <div className="mt-2">
            <ProfileDocsNote profileId={caseItem.profile.id} />
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          Assigned to
          <select
            value={caseItem.assignee?.id ?? ""}
            onChange={(e) =>
              updateCase.mutate({
                assigned_to: e.target.value ? Number(e.target.value) : null,
              })
            }
            className={`${fieldBase} py-1.5`}
          >
            <option value="">Nobody</option>
            {assignees.map((u) => (
              <option key={u.id} value={u.id}>
                {u.email}
              </option>
            ))}
          </select>
        </label>
      </div>
    </div>
  )
}
