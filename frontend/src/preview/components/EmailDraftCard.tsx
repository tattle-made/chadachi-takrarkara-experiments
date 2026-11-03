import { Paperclip } from "lucide-react"
import { emailView } from "../emailView"
import { usePreviewStore } from "../store"
import { attachmentLabel, SENDER_EMAIL, uniqueDomains } from "../template"
import { btnLink, inputBase, inputClass, labelClass } from "./ui"

export function EmailDraftCard({ emailId }: { emailId: string }) {
  const state = usePreviewStore()
  const email = state.emails.find((e) => e.id === emailId)
  if (!email) return null

  const view = emailView(state, email)
  const editable = email.status === "draft"
  const activeGrounds = state.legalGrounds.filter(
    (g) => g.active || email.legalGroundIds.includes(g.id),
  )

  const toggle = (list: string[], id: string) =>
    list.includes(id) ? list.filter((x) => x !== id) : [...list, id]

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_18rem]">
      {/* ── Email ─────────────────────────────── */}
      <div className="space-y-4">
        <div className="grid grid-cols-[4rem_1fr] items-center gap-x-3 gap-y-2 text-sm">
          <span className="text-slate-500">From</span>
          <span className="text-slate-700">
            {SENDER_EMAIL}{" "}
            <span className="text-xs text-slate-400">
              (shared Gmail, mocked)
            </span>
          </span>

          <span className="text-slate-500">To</span>
          {editable ? (
            <select
              value={email.recipientId}
              onChange={(e) =>
                state.updateEmail(email.id, { recipientId: e.target.value })
              }
              className={inputBase}
            >
              {state.recipients.map((r) => (
                <option key={r.id} value={r.id}>
                  {`${r.name} <${r.emails.join(", ")}>`}
                </option>
              ))}
            </select>
          ) : (
            <span className="text-slate-700">
              {`${view.recipient?.name} <${view.recipient?.emails.join(", ")}>`}
            </span>
          )}

          <span className="text-slate-500">Subject</span>
          {editable ? (
            <input
              value={email.subject}
              onChange={(e) =>
                state.updateEmail(email.id, { subject: e.target.value })
              }
              className={inputBase}
            />
          ) : (
            <span className="text-slate-700">{email.subject}</span>
          )}
        </div>

        <div>
          <div className="mb-1 flex items-center justify-between">
            <span className={labelClass}>Email body</span>
            {editable && email.customBody !== null && (
              <button
                type="button"
                onClick={() =>
                  state.updateEmail(email.id, { customBody: null })
                }
                className={btnLink}
              >
                Reset to template
              </button>
            )}
          </div>
          {editable && email.customBody !== null && (
            <p className="mb-2 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">
              Edited by hand. Changing clauses or attachments won't update the
              text until you reset it to the template.
            </p>
          )}
          {editable ? (
            <textarea
              value={view.body}
              onChange={(e) =>
                state.updateEmail(email.id, { customBody: e.target.value })
              }
              rows={22}
              className={`${inputClass} font-mono text-xs leading-relaxed`}
            />
          ) : (
            <div className="whitespace-pre-wrap rounded-md border border-slate-200 bg-slate-50 px-3 py-2 font-mono text-xs leading-relaxed text-slate-700">
              {view.body}
            </div>
          )}
        </div>
      </div>

      {/* ── Side panel ────────────────────────── */}
      <div className="space-y-6 text-sm">
        <div>
          <h4 className="mb-2 font-medium text-slate-700">
            Links ({view.links.length})
          </h4>
          <ul className="space-y-2">
            {uniqueDomains(view.links).map((domain) => (
              <li key={domain}>
                <p className="text-xs font-medium text-slate-500">{domain}</p>
                {view.links
                  .filter((l) => l.domain === domain)
                  .map((l) => (
                    <p key={l.id} className="break-all text-xs text-slate-700">
                      {l.url}
                    </p>
                  ))}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h4 className="mb-2 font-medium text-slate-700">Legal grounds</h4>
          <div className="space-y-2">
            {activeGrounds.map((g) => (
              <label key={g.id} className="flex items-start gap-2">
                <input
                  type="checkbox"
                  disabled={!editable}
                  checked={email.legalGroundIds.includes(g.id)}
                  onChange={() =>
                    state.updateEmail(email.id, {
                      legalGroundIds: toggle(email.legalGroundIds, g.id),
                    })
                  }
                  className="mt-0.5"
                />
                <span>
                  <span className="block text-slate-700">{g.title}</span>
                  <span className="block text-xs text-slate-400">
                    {g.citation}
                  </span>
                </span>
              </label>
            ))}
          </div>
        </div>

        <div>
          <h4 className="mb-1 font-medium text-slate-700">Attachments</h4>
          {view.available.length === 0 ? (
            <p className="text-xs text-slate-400">
              No documents on {view.profile?.fullName}'s profile yet.
            </p>
          ) : (
            <div className="space-y-2">
              {editable && (
                <p className="text-xs text-slate-400">
                  From {view.profile?.fullName}'s profile. Tick the ones to
                  attach.
                </p>
              )}
              {view.available.map((a) => (
                <label key={a.id} className="flex items-start gap-2">
                  <input
                    type="checkbox"
                    disabled={!editable}
                    checked={email.attachmentIds.includes(a.id)}
                    onChange={() =>
                      state.updateEmail(email.id, {
                        attachmentIds: toggle(email.attachmentIds, a.id),
                      })
                    }
                    className="mt-0.5"
                  />
                  <span>
                    <span className="block text-slate-700">
                      {attachmentLabel(a)}
                    </span>
                    <span className="flex items-center gap-1 text-xs text-slate-400">
                      <Paperclip className="size-3" />
                      {a.fileName} · {a.sizeKb} KB
                    </span>
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>

        {email.status === "sent" && email.gmailMessageId && (
          <p className="text-xs text-slate-400">
            Gmail message ID: {email.gmailMessageId}. Replies continue in the
            shared inbox.
          </p>
        )}
      </div>
    </div>
  )
}
