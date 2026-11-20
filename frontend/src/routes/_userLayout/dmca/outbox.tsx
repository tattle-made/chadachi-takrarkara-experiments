import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import { EmailList } from "@/dmca/components/EmailList"
import { profileName } from "@/dmca/labels"
import type { ProfileSummary, TakedownEmail } from "@/dmca/types"
import { fieldBase } from "@/dmca/ui"
import { emailsQueryOptions } from "@/queries/dmca/emails.query"
import { casesQueryOptions } from "@/queries/dmca/profiles.query"

export const Route = createFileRoute("/_userLayout/dmca/outbox")({
  component: OutboxPage,
})

// the tabs: a label and which emails it shows
const FILTERS: {
  value: string
  label: string
  match: (e: TakedownEmail) => boolean
}[] = [
  { value: "all", label: "All", match: () => true },
  { value: "draft", label: "Drafts", match: (e) => e.status === "draft" },
  {
    value: "sending",
    label: "Sending",
    match: (e) => e.status === "queued" || e.status === "sending",
  },
  { value: "sent", label: "Sent", match: (e) => e.status === "sent" },
  { value: "failed", label: "Failed", match: (e) => e.status === "failed" },
  { value: "no_reply", label: "No reply · 48h+", match: (e) => e.no_reply_48h },
]

/** Every takedown email across all cases, with status tabs and a
 * filter by person. */
function OutboxPage() {
  const { data: allEmails = [], isPending } = useQuery(emailsQueryOptions())
  const { data: cases } = useQuery(casesQueryOptions())
  const [filter, setFilter] = useState("all")
  const [personId, setPersonId] = useState("")
  const active = FILTERS.find((f) => f.value === filter) ?? FILTERS[0]

  // whose email each one is, through its case
  const personOf = (email: TakedownEmail) =>
    cases?.data.find((c) => c.id === email.case_id)?.profile
  // everyone with at least one email, by name
  const people = [
    ...new Map(
      allEmails
        .map(personOf)
        .filter((p): p is ProfileSummary => !!p)
        .map((p) => [p.id, p]),
    ).values(),
  ].sort((a, b) => profileName(a).localeCompare(profileName(b)))
  const emails = personId
    ? allEmails.filter((e) => personOf(e)?.id === personId)
    : allEmails

  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Outbox</h1>
        <p className="mt-0.5 text-sm text-slate-600">
          Every takedown email across all cases.
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              onClick={() => setFilter(f.value)}
              className={`rounded-md px-3 py-1.5 text-sm ${
                filter === f.value
                  ? "bg-slate-900 text-white"
                  : "text-slate-700 hover:bg-slate-100"
              }`}
            >
              {f.label}{" "}
              <span className="opacity-60">
                {emails.filter(f.match).length}
              </span>
            </button>
          ))}
        </div>
        <select
          value={personId}
          onChange={(e) => setPersonId(e.target.value)}
          aria-label="Filter by person"
          className={fieldBase}
        >
          <option value="">Everyone</option>
          {people.map((p) => (
            <option key={p.id} value={p.id}>
              {profileName(p)}
            </option>
          ))}
        </select>
      </div>

      {isPending ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : (
        <EmailList
          emails={emails.filter(active.match)}
          showCase
          showPerson
          emptyText="Nothing here."
        />
      )}
    </section>
  )
}
