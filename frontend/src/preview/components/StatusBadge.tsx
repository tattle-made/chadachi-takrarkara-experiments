import { Loader2 } from "lucide-react"
import type { EmailStatus, RecipientKind } from "../types"

const STATUS_STYLE: Record<EmailStatus, string> = {
  draft: "bg-slate-100 text-slate-700",
  queued: "bg-amber-50 text-amber-700",
  sending: "bg-blue-50 text-blue-700",
  sent: "bg-green-50 text-green-700",
  failed: "bg-red-50 text-red-700",
}

export function StatusBadge({
  status,
  attempts,
}: {
  status: EmailStatus
  attempts?: number
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_STYLE[status]}`}
    >
      {(status === "sending" || status === "queued") && (
        <Loader2 className="size-3 animate-spin" />
      )}
      {status}
      {status === "sending" && attempts ? ` · attempt ${attempts}` : ""}
    </span>
  )
}

export function KindBadge({ kind }: { kind: RecipientKind }) {
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
        kind === "platform"
          ? "bg-purple-50 text-purple-700"
          : "bg-orange-50 text-orange-700"
      }`}
    >
      {kind === "platform" ? "Platform" : "Service provider"}
    </span>
  )
}
