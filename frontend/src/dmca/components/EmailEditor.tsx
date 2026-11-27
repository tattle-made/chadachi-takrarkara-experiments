import { useQuery } from "@tanstack/react-query"
import { Paperclip, X } from "lucide-react"
import { useEffect, useState } from "react"
import {
  ATTACHMENT_KIND_LABELS,
  EMAIL_TYPE_LABELS,
  formatSize,
} from "@/dmca/labels"
import type { EmailUpdate, TakedownEmail } from "@/dmca/types"
import {
  btnLink,
  btnPrimary,
  btnSecondary,
  inputBase,
  inputClass,
  labelClass,
} from "@/dmca/ui"
import { attachmentsQueryOptions } from "@/queries/dmca/attachments.query"
import {
  googleStatusQueryOptions,
  legalGroundsQueryOptions,
  recipientsQueryOptions,
} from "@/queries/dmca/config.query"
import { useDeleteEmail, useUpdateEmail } from "@/queries/dmca/emails.query"
import { caseQueryOptions } from "@/queries/dmca/profiles.query"

type Props = {
  email: TakedownEmail
  onDeleted: () => void
}

/** One email opened from the list. A draft can be edited: To address,
 * subject, body, links, legal grounds and attachments. Others are read-only. */
export function EmailEditor({ email, onDeleted }: Props) {
  const editable = email.status === "draft"
  const update = useUpdateEmail()
  const remove = useDeleteEmail()
  const { data: caseItem } = useQuery(caseQueryOptions(email.case_id))
  const { data: google } = useQuery(googleStatusQueryOptions())
  const { data: recipients } = useQuery(recipientsQueryOptions())
  const { data: grounds } = useQuery(legalGroundsQueryOptions())
  const { data: documents = [] } = useQuery({
    ...attachmentsQueryOptions(caseItem?.profile.id ?? ""),
    enabled: !!caseItem,
  })

  // subject and body are typed here and saved with "Save changes"; the
  // ticks and dropdowns save straight away
  const [subject, setSubject] = useState(email.subject)
  const [body, setBody] = useState(email.body)
  const [subjectTyped, setSubjectTyped] = useState(false)
  const [bodyTyped, setBodyTyped] = useState(false)

  // pick up the server's new text (e.g. after ticking a clause) unless the
  // counsellor is in the middle of typing
  useEffect(() => {
    if (!subjectTyped) setSubject(email.subject)
  }, [email.subject, subjectTyped])
  useEffect(() => {
    if (!bodyTyped) setBody(email.body)
  }, [email.body, bodyTyped])

  const save = (changes: EmailUpdate) =>
    update.mutate({ id: email.id, ...changes })

  const saveText = () => {
    const changes: EmailUpdate = {}
    if (subjectTyped) changes.subject = subject
    // only a typed body becomes custom; otherwise it stays generated
    if (bodyTyped) changes.custom_body = body
    update.mutate(
      { id: email.id, ...changes },
      {
        onSuccess: () => {
          setSubjectTyped(false)
          setBodyTyped(false)
        },
      },
    )
  }

  const resetBody = () =>
    update.mutate(
      { id: email.id, custom_body: null },
      { onSuccess: () => setBodyTyped(false) },
    )

  const onDelete = () => {
    if (window.confirm("Delete this draft? Its links stay in the case.")) {
      remove.mutate(email.id, { onSuccess: onDeleted })
    }
  }

  const toggle = (ids: string[], id: string) =>
    ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]

  const recipient = recipients?.data.find((r) => r.id === email.recipient_id)
  const groundIds = email.legal_grounds.map((g) => g.id)
  const attachmentIds = email.attachments.map((a) => a.id)
  // on a draft: the active grounds that fit this case, plus any already on it
  const groundChoices = editable
    ? [
        ...(grounds?.data ?? []).filter(
          (g) =>
            (!g.minor_only || caseItem?.is_minor) && !groundIds.includes(g.id),
        ),
        ...email.legal_grounds,
      ].sort((a, b) => a.title.localeCompare(b.title))
    : email.legal_grounds
  const documentChoices = editable ? documents : email.attachments
  const textTyped = subjectTyped || bodyTyped

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
      {/* the email itself */}
      <div className="space-y-4">
        <div className="grid grid-cols-[4.5rem_1fr] items-center gap-x-3 gap-y-2 text-sm">
          <span className="text-slate-600">From</span>
          <span className="text-slate-800">
            {google?.account_email ?? "The connected Google account"}
          </span>

          <span className="text-slate-600">To</span>
          {editable && recipient && recipient.emails.length > 0 ? (
            <select
              value={email.to_address ?? ""}
              onChange={(e) => save({ to_address: e.target.value })}
              aria-label="To address"
              className={inputBase}
            >
              {!email.to_address && <option value="">Pick an address…</option>}
              {recipient.emails.map((a) => (
                <option key={a.id} value={a.address}>
                  {email.recipient_name} &lt;{a.address}&gt; ·{" "}
                  {EMAIL_TYPE_LABELS[a.email_type]}
                </option>
              ))}
            </select>
          ) : (
            <span className="text-slate-800">
              {email.recipient_name} &lt;{email.to_address ?? "no address"}&gt;
            </span>
          )}

          <span className="text-slate-600">Subject</span>
          {editable ? (
            <input
              value={subject}
              onChange={(e) => {
                setSubject(e.target.value)
                setSubjectTyped(true)
              }}
              aria-label="Subject"
              className={inputBase}
            />
          ) : (
            <span className="text-slate-800">{email.subject}</span>
          )}
        </div>

        <div>
          <div className="mb-1 flex items-center justify-between">
            <span className={labelClass}>Email body</span>
            {editable && email.is_body_custom && (
              <button type="button" onClick={resetBody} className={btnLink}>
                Reset to template
              </button>
            )}
          </div>
          {editable && email.is_body_custom && (
            <p className="mb-2 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">
              Edited by hand. Ticking clauses won't change this text until you
              reset it to the template.
            </p>
          )}
          {editable ? (
            <textarea
              value={body}
              onChange={(e) => {
                setBody(e.target.value)
                setBodyTyped(true)
              }}
              rows={22}
              aria-label="Email body"
              className={`${inputClass} font-mono text-xs leading-relaxed`}
            />
          ) : (
            <div className="whitespace-pre-wrap rounded-md border border-slate-200 bg-white px-3 py-2 font-mono text-xs leading-relaxed text-slate-800">
              {email.body}
            </div>
          )}
        </div>

        {editable && (
          <div className="flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={onDelete}
              disabled={remove.isPending}
              className={`${btnLink} hover:text-red-600`}
            >
              Delete draft
            </button>
            <div className="flex items-center gap-3">
              {textTyped && (
                <span className="text-xs text-amber-700">Unsaved changes</span>
              )}
              {textTyped && (
                <button
                  type="button"
                  onClick={() => {
                    setSubjectTyped(false)
                    setBodyTyped(false)
                  }}
                  className={btnSecondary}
                >
                  Discard
                </button>
              )}
              <button
                type="button"
                onClick={saveText}
                disabled={!textTyped || !subject.trim() || update.isPending}
                className={btnPrimary}
              >
                {update.isPending ? "Saving…" : "Save changes"}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* links, legal grounds, documents */}
      <div className="space-y-6 text-sm">
        <div>
          <h4 className="mb-1 font-medium text-slate-800">
            Links ({email.links.length})
          </h4>
          {editable && (
            <p className="mb-2 text-xs text-slate-500">
              A link taken out stays in the case, as "not emailed yet". To put
              it back, click "Draft emails" on the case's links and add it to
              this draft.
            </p>
          )}
          <ul className="space-y-1">
            {email.links.map((l) => (
              <li key={l.id} className="flex items-start gap-1.5">
                <span className="break-all text-xs text-slate-800">
                  {l.url}
                </span>
                {editable && email.links.length > 1 && (
                  <button
                    type="button"
                    onClick={() =>
                      save({
                        link_ids: email.links
                          .filter((x) => x.id !== l.id)
                          .map((x) => x.id),
                      })
                    }
                    aria-label={`Take ${l.url} out of this email`}
                    className="text-slate-400 hover:text-red-600"
                  >
                    <X className="size-3.5" />
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h4 className="mb-2 font-medium text-slate-800">Legal grounds</h4>
          {groundChoices.length === 0 ? (
            <p className="text-xs text-slate-500">None.</p>
          ) : (
            <div className="space-y-2">
              {groundChoices.map((g) => (
                <label key={g.id} className="flex items-start gap-2">
                  <input
                    type="checkbox"
                    disabled={!editable || update.isPending}
                    checked={groundIds.includes(g.id)}
                    onChange={() =>
                      save({ legal_ground_ids: toggle(groundIds, g.id) })
                    }
                    className="mt-0.5"
                  />
                  <span>
                    <span className="block text-slate-800">{g.title}</span>
                    <span className="block text-xs text-slate-500">
                      {g.citation}
                    </span>
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>

        <div>
          <h4 className="mb-1 font-medium text-slate-800">Attachments</h4>
          {documentChoices.length === 0 ? (
            <p className="text-xs text-slate-500">
              {editable
                ? "No documents on this person's profile yet."
                : "None."}
            </p>
          ) : (
            <div className="space-y-2">
              {editable && (
                <p className="text-xs text-slate-500">
                  From the profile's documents. Tick the ones to attach.
                </p>
              )}
              {documentChoices.map((a) => (
                <label key={a.id} className="flex items-start gap-2">
                  <input
                    type="checkbox"
                    disabled={!editable || update.isPending}
                    checked={attachmentIds.includes(a.id)}
                    onChange={() =>
                      save({ attachment_ids: toggle(attachmentIds, a.id) })
                    }
                    className="mt-0.5"
                  />
                  <span>
                    <span className="block text-slate-800">
                      {ATTACHMENT_KIND_LABELS[a.kind]}
                    </span>
                    <span className="flex items-center gap-1 text-xs text-slate-500">
                      <Paperclip className="size-3" />
                      {a.file_name} · {formatSize(a.size)}
                    </span>
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>

        {email.status === "sent" && (
          <p className="text-xs text-slate-500">
            Replies arrive in the shared Gmail inbox. Tick "Got a reply" in the
            list when one comes in.
          </p>
        )}
      </div>
    </div>
  )
}
