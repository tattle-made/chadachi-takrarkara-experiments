import * as Tooltip from "@radix-ui/react-tooltip"
import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import {
  ChevronDown,
  ChevronRight,
  Clock,
  Loader2,
  RotateCw,
  Send,
  TrendingUp,
} from "lucide-react"
import { Fragment, useState } from "react"
import { profileName, STATUS_LABELS } from "@/dmca/labels"
import type { EmailStatus, TakedownEmail } from "@/dmca/types"
import { btnPrimary, cardClass, formatDate, tdClass, thClass } from "@/dmca/ui"
import { useRetryEmail, useSetReplyReceived } from "@/queries/dmca/emails.query"
import { casesQueryOptions } from "@/queries/dmca/profiles.query"
import { EmailEditor } from "./EmailEditor"
import { SendConfirmDialog } from "./SendConfirmDialog"

const STATUS_STYLE: Record<EmailStatus, string> = {
  draft: "bg-slate-100 text-slate-700",
  queued: "bg-amber-50 text-amber-700",
  sending: "bg-blue-50 text-blue-700",
  sent: "bg-green-50 text-green-700",
  failed: "bg-red-50 text-red-700",
}

type Props = {
  emails: TakedownEmail[]
  // add a Case column (outbox, profile page)
  showCase?: boolean
  // put the person's name above the case (outbox)
  showPerson?: boolean
  emptyText?: string
}

/** The emails table: tick drafts and send them, open one to edit or view it,
 * Retry failed ones, and mark replies / Escalate on sent ones. */
export function EmailList({
  emails,
  showCase = false,
  showPerson = false,
  emptyText = "No emails yet.",
}: Props) {
  const [selected, setSelected] = useState<string[]>([])
  const [openId, setOpenId] = useState<string | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const { data: cases } = useQuery({
    ...casesQueryOptions(),
    enabled: showCase,
  })
  const caseOf = (id: string) => cases?.data.find((c) => c.id === id)

  const draftIds = emails.filter((e) => e.status === "draft").map((e) => e.id)
  // a draft may have been sent or deleted since it was ticked
  const selectedDrafts = selected.filter((id) => draftIds.includes(id))
  const allSelected =
    draftIds.length > 0 && selectedDrafts.length === draftIds.length

  const toggle = (id: string) =>
    setSelected((s) =>
      s.includes(id) ? s.filter((x) => x !== id) : [...s, id],
    )

  if (emails.length === 0) {
    return <p className="text-sm text-slate-500">{emptyText}</p>
  }

  const columnCount = showCase ? 6 : 5

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-600">
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

      <div className={`overflow-x-auto ${cardClass}`}>
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
              <th className={thClass}>To</th>
              <th className={thClass}>Subject</th>
              {showCase && (
                <th className={thClass}>
                  {showPerson ? "Person / case" : "Case"}
                </th>
              )}
              <th className={thClass}>Status</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {emails.map((email) => {
              const isOpen = openId === email.id
              const caseItem = showCase ? caseOf(email.case_id) : undefined
              return (
                <Fragment key={email.id}>
                  <tr className="border-b border-slate-100 last:border-0">
                    <td className={tdClass}>
                      <input
                        type="checkbox"
                        aria-label="Select email"
                        disabled={email.status !== "draft"}
                        checked={selectedDrafts.includes(email.id)}
                        onChange={() => toggle(email.id)}
                      />
                    </td>
                    <td className={tdClass}>
                      <p className="font-medium text-slate-900">
                        {email.recipient_name}
                      </p>
                      <p className="text-xs text-slate-600">
                        {email.to_address ?? (
                          <span className="text-amber-700">No address</span>
                        )}
                      </p>
                    </td>
                    <td className={tdClass}>
                      <p className="text-slate-800">{email.subject}</p>
                      <p className="text-xs text-slate-500">
                        {count(email.links.length, "link")} ·{" "}
                        {email.attachments.length === 0 ? (
                          <span className="text-amber-700">no attachments</span>
                        ) : (
                          count(email.attachments.length, "attachment")
                        )}
                      </p>
                    </td>
                    {showCase && (
                      <td className={tdClass}>
                        {showPerson && caseItem && (
                          <p className="font-medium text-slate-900">
                            {profileName(caseItem.profile)}
                          </p>
                        )}
                        <Link
                          to="/dmca/cases/$caseId"
                          params={{ caseId: email.case_id }}
                          className={`hover:underline ${
                            showPerson
                              ? "text-xs text-slate-600"
                              : "text-slate-800"
                          }`}
                        >
                          {caseItem?.title ?? "Open case"}
                        </Link>
                      </td>
                    )}
                    <td className={tdClass}>
                      <EmailStatusCell email={email} />
                    </td>
                    <td className={`${tdClass} text-right`}>
                      <RowActions
                        email={email}
                        isOpen={isOpen}
                        onToggleOpen={() => setOpenId(isOpen ? null : email.id)}
                      />
                    </td>
                  </tr>
                  {isOpen && (
                    <tr className="border-b border-slate-100 bg-slate-50/60">
                      <td colSpan={columnCount} className="px-4 py-5">
                        <EmailEditor
                          email={email}
                          onDeleted={() => setOpenId(null)}
                        />
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
        onSent={() => setSelected([])}
      />
    </div>
  )
}

/** "1 link", "3 links". */
const count = (n: number, word: string) => `${n} ${n === 1 ? word : `${word}s`}`

/** Status badge, plus when it was sent, why it failed, or reply state. */
function EmailStatusCell({ email }: { email: TakedownEmail }) {
  const inQueue = email.status === "queued" || email.status === "sending"
  return (
    <div className="space-y-1">
      <span
        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[email.status]}`}
      >
        {inQueue && <Loader2 className="size-3 animate-spin" />}
        {STATUS_LABELS[email.status]}
      </span>
      {email.status === "sent" && email.sent_at && (
        <p className="whitespace-nowrap text-xs text-slate-500">
          {formatDate(email.sent_at)}
        </p>
      )}
      {email.status === "failed" && email.last_error && (
        <p className="max-w-56 text-xs text-red-700">{email.last_error}</p>
      )}
      {email.reply_received_at && (
        <p className="text-xs font-medium text-green-700">Got a reply</p>
      )}
      {email.no_reply_48h && (
        <p className="inline-flex items-center gap-1 whitespace-nowrap text-xs font-medium text-amber-700">
          <Clock className="size-3" />
          No reply · 48h+
        </p>
      )}
    </div>
  )
}

/** Retry (failed), Got a reply + Escalate (sent), and Edit / View. */
function RowActions({
  email,
  isOpen,
  onToggleOpen,
}: {
  email: TakedownEmail
  isOpen: boolean
  onToggleOpen: () => void
}) {
  const retry = useRetryEmail()
  const setReply = useSetReplyReceived()

  return (
    <div className="flex flex-wrap items-center justify-end gap-3">
      {email.can_retry && (
        <button
          type="button"
          onClick={() => retry.mutate(email.id)}
          disabled={retry.isPending}
          className="inline-flex items-center gap-1 rounded-md border border-red-200 px-2 py-1 text-xs text-red-700 hover:bg-red-50"
        >
          <RotateCw className="size-3" />
          Retry
        </button>
      )}
      {email.status === "sent" && (
        <>
          <label className="inline-flex items-center gap-1.5 text-xs text-slate-700">
            <input
              type="checkbox"
              checked={email.reply_received_at !== null}
              disabled={setReply.isPending}
              onChange={(e) =>
                setReply.mutate({ id: email.id, received: e.target.checked })
              }
            />
            Got a reply
          </label>
          <Tooltip.Provider delayDuration={200}>
            <Tooltip.Root>
              <Tooltip.Trigger asChild>
                <Link
                  to="/dmca/cases/$caseId"
                  params={{ caseId: email.case_id }}
                  search={{ escalate: email.id }}
                  className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-800 hover:bg-slate-100"
                >
                  <TrendingUp className="size-3" />
                  Escalate
                </Link>
              </Tooltip.Trigger>
              <Tooltip.Portal>
                <Tooltip.Content
                  side="top"
                  sideOffset={4}
                  className="max-w-56 rounded-md bg-slate-900 px-2 py-1 text-xs text-white shadow"
                >
                  Opens the escalation review on this email's case page
                  <Tooltip.Arrow className="fill-slate-900" />
                </Tooltip.Content>
              </Tooltip.Portal>
            </Tooltip.Root>
          </Tooltip.Provider>
        </>
      )}
      <button
        type="button"
        onClick={onToggleOpen}
        className="inline-flex items-center gap-1 text-xs text-slate-600 hover:text-slate-900"
      >
        {isOpen ? (
          <ChevronDown className="size-4" />
        ) : (
          <ChevronRight className="size-4" />
        )}
        {email.status === "draft" ? "Edit" : "View"}
      </button>
    </div>
  )
}
