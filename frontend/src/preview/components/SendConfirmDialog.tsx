import * as Dialog from "@radix-ui/react-dialog"
import { AlertTriangle } from "lucide-react"
import type { Recipient, TakedownEmail } from "../types"
import { btnPrimary, btnSecondary } from "@/dmca/ui"

export function SendConfirmDialog({
  emails,
  recipients,
  open,
  onOpenChange,
  onConfirm,
}: {
  emails: TakedownEmail[]
  recipients: Recipient[]
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
}) {
  const withoutAttachments = emails.filter(
    (e) => e.attachmentIds.length === 0,
  ).length

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/30" />
        <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl">
          <Dialog.Title className="text-base font-semibold text-slate-900">
            Send {emails.length} {emails.length === 1 ? "email" : "emails"}?
          </Dialog.Title>
          <Dialog.Description className="mt-1 text-sm text-slate-500">
            They'll be queued and sent from the shared Gmail one by one. Sent
            emails can't be edited or sent again.
          </Dialog.Description>
          {withoutAttachments > 0 && (
            <p className="mt-4 flex items-start gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
              {withoutAttachments === emails.length
                ? emails.length === 1
                  ? "This email has no attachments."
                  : "None of these emails have attachments."
                : `${withoutAttachments} of these emails ${withoutAttachments === 1 ? "has" : "have"} no attachments.`}{" "}
              You can still send, or cancel and tick documents on each email.
            </p>
          )}
          <ul className="mt-4 max-h-64 space-y-2 overflow-y-auto">
            {emails.map((e) => {
              const r = recipients.find((x) => x.id === e.recipientId)
              return (
                <li
                  key={e.id}
                  className="rounded-md border border-slate-100 bg-slate-50 px-3 py-2 text-sm"
                >
                  <p className="font-medium text-slate-800">
                    {r?.name}{" "}
                    <span className="font-normal text-slate-500">
                      &lt;{r?.emails.join(", ")}&gt;
                    </span>
                  </p>
                  <p className="text-xs text-slate-500">
                    {e.subject} · {e.linkIds.length}{" "}
                    {e.linkIds.length === 1 ? "link" : "links"} ·{" "}
                    {e.attachmentIds.length === 0 ? (
                      <span className="text-amber-700">no attachments</span>
                    ) : (
                      `${e.attachmentIds.length} ${e.attachmentIds.length === 1 ? "attachment" : "attachments"}`
                    )}
                  </p>
                </li>
              )
            })}
          </ul>
          <div className="mt-6 flex justify-end gap-3">
            <Dialog.Close asChild>
              <button type="button" className={btnSecondary}>
                Cancel
              </button>
            </Dialog.Close>
            <button type="button" onClick={onConfirm} className={btnPrimary}>
              Send now
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
