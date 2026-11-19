import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { Download, Paperclip, Upload } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"
import { ATTACHMENT_KIND_LABELS, formatSize, profileName } from "@/dmca/labels"
import type { AttachmentKind } from "@/dmca/types"
import { cardClass, fieldBase, formatDate } from "@/dmca/ui"
import {
  attachmentsQueryOptions,
  downloadAttachment,
  useUploadAttachment,
} from "@/queries/dmca/attachments.query"
import { profileQueryOptions } from "@/queries/dmca/profiles.query"

// same limit as the backend (MAX_ATTACHMENT_MB), checked here to skip the upload
const MAX_UPLOAD_MB = 18

const KIND_OPTIONS = Object.entries(ATTACHMENT_KIND_LABELS) as [
  AttachmentKind,
  string,
][]

/** Short pointer on case screens: documents live on the profile. */
export function ProfileDocsNote({ profileId }: { profileId: string }) {
  const { data: profile } = useQuery(profileQueryOptions(profileId))
  const { data: attachments } = useQuery(attachmentsQueryOptions(profileId))
  if (!profile || !attachments) return null
  const count = attachments.length
  const name = profileName(profile)

  return (
    <p className="flex items-center gap-2 text-xs text-slate-500">
      <Paperclip className="size-3.5 text-slate-400" />
      <span>
        {count === 0
          ? `No documents on ${name}'s profile yet.`
          : `${count} ${count === 1 ? "document" : "documents"} on ${name}'s profile.`}{" "}
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

/** A person's documents, used across all their emails. Add-only, so sent
 * emails keep a full record of what was attached. */
export function DocumentsPanel({ profileId }: { profileId: string }) {
  const { data: attachments = [], isPending } = useQuery(
    attachmentsQueryOptions(profileId),
  )
  const upload = useUploadAttachment(profileId)
  const [kind, setKind] = useState<AttachmentKind>("cyber_crime_report")

  /** Upload the picked files one by one; a failed one doesn't stop the rest. */
  const uploadFiles = async (files: File[]) => {
    for (const file of files) {
      if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
        toast.error(`${file.name} is over ${MAX_UPLOAD_MB} MB`)
        continue
      }
      try {
        await upload.mutateAsync({ kind, file })
      } catch {
        // the hook already showed the error
      }
    }
  }

  return (
    <div className={`${cardClass} p-4`}>
      <p className="text-xs text-slate-500">
        Upload this person's documents here once. They can be used in any of
        their cases. On each email, choose which ones to attach; nothing is
        attached by default.
      </p>

      {isPending ? (
        <p className="mt-3 text-sm text-slate-400">Loading…</p>
      ) : (
        attachments.length > 0 && (
          <ul className="mt-3 space-y-2">
            {attachments.map((a) => (
              <li key={a.id} className="flex items-center gap-2 text-sm">
                <Paperclip className="size-4 text-slate-400" />
                <span className="font-medium text-slate-700">
                  {ATTACHMENT_KIND_LABELS[a.kind]}
                </span>
                <span className="text-xs text-slate-400">
                  {a.file_name} · {formatSize(a.size)} · added{" "}
                  {formatDate(a.created_at)}
                </span>
                <button
                  type="button"
                  onClick={() => downloadAttachment(a)}
                  aria-label={`Download ${a.file_name}`}
                  className="text-slate-400 hover:text-slate-900"
                >
                  <Download className="size-4" />
                </button>
              </li>
            ))}
          </ul>
        )
      )}

      <div className="mt-3 flex items-center gap-2">
        <select
          value={kind}
          onChange={(e) => setKind(e.target.value as AttachmentKind)}
          aria-label="Document type"
          className={`${fieldBase} w-56 py-1.5 text-xs`}
        >
          {KIND_OPTIONS.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <label
          className={`inline-flex items-center gap-2 rounded-md border border-dashed border-slate-300 px-3 py-1.5 text-xs text-slate-600 ${
            upload.isPending
              ? "cursor-wait opacity-60"
              : "cursor-pointer hover:bg-slate-50"
          }`}
        >
          <Upload className="size-3.5" />
          {upload.isPending ? "Uploading…" : "Add files"}
          <input
            type="file"
            multiple
            disabled={upload.isPending}
            className="hidden"
            onChange={(e) => {
              const files = [...(e.target.files ?? [])]
              e.target.value = ""
              if (files.length > 0) uploadFiles(files)
            }}
          />
        </label>
      </div>
    </div>
  )
}
