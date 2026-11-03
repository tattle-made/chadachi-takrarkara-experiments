import { Link } from "@tanstack/react-router"
import { ChevronDown, ChevronRight, RotateCw, Send } from "lucide-react"
import { Fragment, useState } from "react"
import { usePreviewStore } from "../store"
import type { TakedownEmail } from "../types"
import { EmailDraftCard } from "./EmailDraftCard"
import { SendConfirmDialog } from "./SendConfirmDialog"
import { KindBadge, StatusBadge } from "./StatusBadge"
import { btnPrimary, cardClass, formatDate, tdClass, thClass } from "./ui"

// Select-and-send table shared by the case page, profile page and outbox.
// Only drafts can be selected; sent emails are locked, failed ones get Retry.
export function EmailList({
  emails,
  showCase = false,
  emptyText = "No emails yet.",
}: {
  emails: TakedownEmail[]
  showCase?: boolean
  emptyText?: string
}) {
  const state = usePreviewStore()
  const [selected, setSelected] = useState<string[]>([])
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)

  const draftIds = emails.filter((e) => e.status === "draft").map((e) => e.id)
  const selectedDrafts = selected.filter((id) => draftIds.includes(id))
  const allSelected =
    draftIds.length > 0 && selectedDrafts.length === draftIds.length

  const toggle = (id: string) =>
    setSelected((s) =>
      s.includes(id) ? s.filter((x) => x !== id) : [...s, id],
    )

  const confirmSend = () => {
    state.sendEmails(selectedDrafts)
    setSelected([])
    setConfirmOpen(false)
  }

  if (emails.length === 0) {
    return <p className="text-sm text-slate-400">{emptyText}</p>
  }

  const columnCount = showCase ? 6 : 5

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          {selectedDrafts.length > 0
            ? `${selectedDrafts.length} selected`
            : `${draftIds.length} ${draftIds.length === 1 ? "draft" : "drafts"} ready to send`}
        </p>
        <button
          type="button"
          disabled={selectedDrafts.length === 0}
          onClick={() => setConfirmOpen(true)}
          className={`${btnPrimary} inline-flex items-center gap-2`}
        >
          <Send className="size-4" />
          Send selected
          {selectedDrafts.length > 0 ? ` (${selectedDrafts.length})` : ""}
        </button>
      </div>

      <div className={`overflow-hidden ${cardClass}`}>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className="w-10 px-4 py-3">
                <input
                  type="checkbox"
                  aria-label="Select all drafts"
                  disabled={draftIds.length === 0}
                  checked={allSelected}
                  onChange={() => setSelected(allSelected ? [] : draftIds)}
                />
              </th>
              <th className={thClass}>Recipient</th>
              <th className={thClass}>Subject</th>
              {showCase && <th className={thClass}>Case</th>}
              <th className={thClass}>Status</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {emails.map((email) => {
              const recipient = state.recipients.find(
                (r) => r.id === email.recipientId,
              )
              const caseItem = state.cases.find((c) => c.id === email.caseId)
              const profile = state.profiles.find(
                (p) => p.id === caseItem?.profileId,
              )
              const isDraft = email.status === "draft"
              const expanded = expandedId === email.id

              return (
                <Fragment key={email.id}>
                  <tr className="border-b border-slate-100 last:border-0">
                    <td className={tdClass}>
                      <input
                        type="checkbox"
                        aria-label="Select email"
                        disabled={!isDraft}
                        checked={selectedDrafts.includes(email.id)}
                        onChange={() => toggle(email.id)}
                      />
                    </td>
                    <td className={tdClass}>
                      <p className="font-medium text-slate-900">
                        {recipient?.name}
                      </p>
                      <p className="text-xs text-slate-500">
                        {recipient?.emails.join(", ")}
                      </p>
                      {recipient && (
                        <div className="mt-1">
                          <KindBadge kind={recipient.kind} />
                        </div>
                      )}
                    </td>
                    <td className={tdClass}>
                      <p className="text-slate-700">{email.subject}</p>
                      <p className="text-xs text-slate-400">
                        {email.linkIds.length}{" "}
                        {email.linkIds.length === 1 ? "link" : "links"} ·{" "}
                        {email.attachmentIds.length}{" "}
                        {email.attachmentIds.length === 1
                          ? "attachment"
                          : "attachments"}
                      </p>
                    </td>
                    {showCase && (
                      <td className={tdClass}>
                        {caseItem && (
                          <Link
                            to="/dmca-ui-preview/cases/$caseId"
                            params={{ caseId: caseItem.id }}
                            className="text-slate-700 hover:underline"
                          >
                            {caseItem.title}
                          </Link>
                        )}
                        <p className="text-xs text-slate-400">
                          {profile?.fullName}
                        </p>
                      </td>
                    )}
                    <td className={tdClass}>
                      <StatusBadge
                        status={email.status}
                        attempts={email.attempts}
                      />
                      {email.status === "sent" && email.sentAt && (
                        <p className="mt-1 text-xs text-slate-400">
                          {formatDate(email.sentAt)}
                        </p>
                      )}
                      {email.status === "failed" && (
                        <p className="mt-1 max-w-48 text-xs text-red-600">
                          {email.lastError} · {email.attempts} attempts
                        </p>
                      )}
                    </td>
                    <td className={`${tdClass} text-right`}>
                      <div className="flex items-center justify-end gap-3">
                        {email.status === "failed" && (
                          <button
                            type="button"
                            onClick={() => state.retryEmail(email.id)}
                            className="inline-flex items-center gap-1 rounded-md border border-red-200 px-2 py-1 text-xs text-red-700 hover:bg-red-50"
                          >
                            <RotateCw className="size-3" />
                            Retry
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() =>
                            setExpandedId(expanded ? null : email.id)
                          }
                          className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-900"
                        >
                          {expanded ? (
                            <ChevronDown className="size-4" />
                          ) : (
                            <ChevronRight className="size-4" />
                          )}
                          {isDraft ? "Edit" : "View"}
                        </button>
                      </div>
                    </td>
                  </tr>
                  {expanded && (
                    <tr className="border-b border-slate-100 bg-slate-50/50">
                      <td colSpan={columnCount} className="px-4 py-5">
                        <EmailDraftCard emailId={email.id} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>

      <SendConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        emails={emails.filter((e) => selectedDrafts.includes(e.id))}
        recipients={state.recipients}
        onConfirm={confirmSend}
      />
    </div>
  )
}
