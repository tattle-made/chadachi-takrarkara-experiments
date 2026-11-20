import * as Dialog from "@radix-ui/react-dialog"
import { AlertTriangle } from "lucide-react"
import { toast } from "sonner"
import type { TakedownEmail } from "@/dmca/types"
import { btnPrimary, btnSecondary } from "@/dmca/ui"
import { useSendEmails } from "@/queries/dmca/emails.query"

type Props = {
  emails: TakedownEmail[]
  open: boolean
  onOpenChange: (open: boolean) => void
  onSent: () => void
}

/** "Send N emails?": lists them, warns about missing attachments or
 * addresses, then hands them to the send queue. */
export function SendConfirmDialog({
  emails,
  open,
  onOpenChange,
  onSent,
}: Props) {
  const send = useSendEmails()
  const noAddress = emails.filter((e) => !e.to_address).length
  const noAttachments = emails.filter((e) => e.attachments.length === 0).length

  const confirm = () =>
    send.mutate(
      emails.map((e) => e.id),
      {
        onSuccess: (queued) => {
          toast.success(
            `${queued.length} ${queued.length === 1 ? "email" : "emails"} queued. They go out one by one.`,
          )
          onSent()
          onOpenChange(false)
        },
      },
    )

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/30" />
        <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl">
          <Dialog.Title className="text-base font-semibold text-slate-900">
            Send {emails.length} {emails.length === 1 ? "email" : "emails"}?
          </Dialog.Title>
          <Dialog.Description className="mt-1 text-sm text-slate-600">
            They're queued and sent from the shared Gmail one by one. Sent
            emails can't be edited.
          </Dialog.Description>

          {noAddress > 0 && (
            <p className="mt-4 flex items-start gap-2 rounded-md bg-red-50 px-3 py-2 text-sm text-red-800">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
              {noAddress === 1
                ? "1 email has no To address."
                : `${noAddress} emails have no To address.`}{" "}
              Add an address to the organisation in Config first.
            </p>
          )}
          {noAttachments > 0 && (
            <p className="mt-4 flex items-start gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
              {noAttachments === emails.length
                ? emails.length === 1
                  ? "This email has no attachments."
                  : "None of these emails have attachments."
                : `${noAttachments} of these emails ${noAttachments === 1 ? "has" : "have"} no attachments.`}{" "}
              You can still send, or cancel and tick documents on each email.
            </p>
          )}

          <ul className="mt-4 max-h-64 space-y-2 overflow-y-auto">
            {emails.map((e) => (
              <li
                key={e.id}
                className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
              >
                <p className="font-medium text-slate-900">
                  {e.recipient_name}{" "}
                  <span className="font-normal text-slate-600">
                    &lt;{e.to_address ?? "no address"}&gt;
                  </span>
                </p>
                <p className="text-xs text-slate-600">
                  {e.subject} · {e.links.length}{" "}
                  {e.links.length === 1 ? "link" : "links"} ·{" "}
                  {e.attachments.length === 0 ? (
                    <span className="text-amber-700">no attachments</span>
                  ) : (
                    `${e.attachments.length} ${e.attachments.length === 1 ? "attachment" : "attachments"}`
                  )}
                </p>
              </li>
            ))}
          </ul>

          <div className="mt-6 flex justify-end gap-3">
            <Dialog.Close asChild>
              <button type="button" className={btnSecondary}>
                Cancel
              </button>
            </Dialog.Close>
            <button
              type="button"
              onClick={confirm}
              disabled={send.isPending || noAddress > 0}
              className={btnPrimary}
            >
              {send.isPending ? "Sending…" : "Send now"}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
