import { createFileRoute } from "@tanstack/react-router"
import { CheckCircle2 } from "lucide-react"
import { useState } from "react"
import { EmailList } from "@/preview/components/EmailList"
import { usePreviewStore } from "@/preview/store"
import { SENDER_EMAIL } from "@/preview/template"
import type { EmailStatus } from "@/preview/types"

export const Route = createFileRoute("/_userLayout/dmca-ui-preview/outbox")({
  component: OutboxPage,
})

type Filter = "all" | "draft" | "in_progress" | "sent" | "failed"

const FILTERS: { value: Filter; label: string; statuses: EmailStatus[] }[] = [
  {
    value: "all",
    label: "All",
    statuses: ["draft", "queued", "sending", "sent", "failed"],
  },
  { value: "draft", label: "Drafts", statuses: ["draft"] },
  { value: "in_progress", label: "Sending", statuses: ["queued", "sending"] },
  { value: "sent", label: "Sent", statuses: ["sent"] },
  { value: "failed", label: "Failed", statuses: ["failed"] },
]

function OutboxPage() {
  const emails = usePreviewStore((s) => s.emails)
  const [filter, setFilter] = useState<Filter>("all")

  const active = FILTERS.find((f) => f.value === filter) ?? FILTERS[0]
  const visible = emails.filter((e) => active.statuses.includes(e.status))

  return (
    <section className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Outbox</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Every takedown email across all cases.
          </p>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-green-200 bg-green-50 px-3 py-1 text-xs text-green-800">
          <CheckCircle2 className="size-3.5" />
          Gmail connected · sending as {SENDER_EMAIL}
        </span>
      </div>

      <div className="flex gap-1">
        {FILTERS.map((f) => {
          const count = emails.filter((e) =>
            f.statuses.includes(e.status),
          ).length
          return (
            <button
              key={f.value}
              type="button"
              onClick={() => setFilter(f.value)}
              className={`rounded-md px-3 py-1.5 text-sm ${
                filter === f.value
                  ? "bg-slate-900 text-white"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              {f.label} <span className="opacity-60">{count}</span>
            </button>
          )
        })}
      </div>

      <EmailList emails={visible} showCase emptyText="Nothing here." />
    </section>
  )
}
