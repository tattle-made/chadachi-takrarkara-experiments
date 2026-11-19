import { Link } from "@tanstack/react-router"
import { Paperclip, Upload } from "lucide-react"
import { useState } from "react"
import { usePreviewStore } from "../store"
import { ATTACHMENT_KIND_OPTIONS } from "../template"
import type { AttachmentKind } from "../types"
import { cardClass, fieldBase, formatDate } from "./ui"

const KIND_LABEL = Object.fromEntries(ATTACHMENT_KIND_OPTIONS) as Record<
  AttachmentKind,
  string
>

// Short pointer shown on case screens: documents live on the profile.
export function ProfileDocsNote({ profileId }: { profileId: string }) {
  const profile = usePreviewStore((s) =>
    s.profiles.find((p) => p.id === profileId),
  )
  const count = usePreviewStore(
    (s) => s.attachments.filter((a) => a.profileId === profileId).length,
  )
  if (!profile) return null

  return (
    <p className="flex items-center gap-2 text-xs text-slate-500">
      <Paperclip className="size-3.5 text-slate-400" />
      <span>
        {count === 0
          ? `No documents on ${profile.fullName}'s profile yet.`
          : `${count} ${count === 1 ? "document" : "documents"} on ${profile.fullName}'s profile.`}{" "}
        Choose which to attach on each email.{" "}
        <Link
          to="/dmca/profiles/$profileId"
          params={{ profileId }}
          className="underline underline-offset-2 hover:text-slate-900"
        >
          {count === 0 ? "Add documents" : "Manage documents"}
        </Link>
      </span>
    </p>
  )
}

// A person's documents, used across all of her emails. Add-only (no delete)
// to keep the trail of what was attached to sent emails.
export function DocumentsPanel({ profileId }: { profileId: string }) {
  const allAttachments = usePreviewStore((s) => s.attachments)
  const addAttachments = usePreviewStore((s) => s.addAttachments)
  const [kind, setKind] = useState<AttachmentKind>("cyber_crime_report")

  const attachments = allAttachments.filter((a) => a.profileId === profileId)

  return (
    <div className={`${cardClass} p-4`}>
      <p className="text-xs text-slate-500">
        Upload all of this person's documents here once. They can be used in any
        of her cases. On each email, choose which ones to attach; nothing is
        attached by default.
      </p>

      {attachments.length > 0 && (
        <ul className="mt-3 space-y-2">
          {attachments.map((a) => (
            <li key={a.id} className="flex items-center gap-2 text-sm">
              <Paperclip className="size-4 text-slate-400" />
              <span className="font-medium text-slate-700">
                {KIND_LABEL[a.kind]}
              </span>
              <span className="text-xs text-slate-400">
                {a.fileName} · {a.sizeKb} KB · added {formatDate(a.uploadedAt)}
              </span>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-3 flex items-center gap-2">
        <select
          value={kind}
          onChange={(e) => setKind(e.target.value as AttachmentKind)}
          aria-label="Document type"
          className={`${fieldBase} w-56 py-1.5 text-xs`}
        >
          {ATTACHMENT_KIND_OPTIONS.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <label className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-dashed border-slate-300 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50">
          <Upload className="size-3.5" />
          Add files
          <input
            type="file"
            multiple
            className="hidden"
            onChange={(e) => {
              const files = [...(e.target.files ?? [])]
              if (files.length > 0) {
                addAttachments(
                  profileId,
                  files.map((file) => ({ kind, file })),
                )
              }
              e.target.value = ""
            }}
          />
        </label>
      </div>
    </div>
  )
}
