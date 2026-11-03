import { AlertTriangle } from "lucide-react"
import { useState } from "react"
import { SAMPLE_LINKS } from "../data"
import { type DraftGroup, usePreviewStore } from "../store"
import { parseLinks, suggestedRecipientId } from "../template"
import {
  btnLink,
  btnPrimary,
  btnSecondary,
  cardClass,
  inputBase,
  inputClass,
  tdClass,
  thClass,
} from "./ui"

type DomainRow = {
  domain: string
  urls: string[]
  known: boolean
  recipientId: string
}

// Paste links → check who each domain goes to → create one draft per
// recipient. Used for a new case and for adding links to an existing case.
export function AddLinksFlow({
  caseId,
  onDone,
  onCancel,
}: {
  caseId: string
  onDone: () => void
  onCancel?: () => void
}) {
  const state = usePreviewStore()
  const [text, setText] = useState("")
  const [rows, setRows] = useState<DomainRow[] | null>(null)
  const [invalid, setInvalid] = useState<string[]>([])
  const [duplicates, setDuplicates] = useState<string[]>([])

  const recipientName = (id: string) =>
    state.recipients.find((r) => r.id === id)?.name ?? ""

  const review = () => {
    const existing = new Set(
      state.links.filter((l) => l.caseId === caseId).map((l) => l.url),
    )
    const parsed = parseLinks(text)
    setInvalid(parsed.filter((p) => !p.domain).map((p) => p.url))
    setDuplicates(
      parsed.filter((p) => p.domain && existing.has(p.url)).map((p) => p.url),
    )

    const byDomain = new Map<string, string[]>()
    for (const p of parsed) {
      if (!p.domain || existing.has(p.url)) continue
      byDomain.set(p.domain, [...(byDomain.get(p.domain) ?? []), p.url])
    }
    setRows(
      [...byDomain.entries()].map(([domain, urls]) => {
        const suggested = suggestedRecipientId(domain, state.domains)
        return {
          domain,
          urls,
          known: suggested !== null,
          recipientId: suggested ?? "",
        }
      }),
    )
  }

  const setRecipient = (domain: string, recipientId: string) =>
    setRows((rs) =>
      rs
        ? rs.map((r) => (r.domain === domain ? { ...r, recipientId } : r))
        : rs,
    )

  // ── Step 1: paste ─────────────────────────────
  if (!rows) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label htmlFor="links" className="text-sm font-medium text-slate-700">
            Paste every link for this case
          </label>
          <button
            type="button"
            onClick={() => setText(SAMPLE_LINKS)}
            className={btnLink}
          >
            Use sample links
          </button>
        </div>
        <textarea
          id="links"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={8}
          placeholder={"https://site-a.com/video/123\nhttps://site-b.net/p/456"}
          className={`${inputClass} font-mono text-xs`}
        />
        <p className="text-xs text-slate-400">
          One per line, or separated by spaces or commas. Links from different
          sites are fine; they'll be grouped by recipient in the next step.
        </p>
        <div className="flex justify-end gap-3">
          {onCancel && (
            <button type="button" onClick={onCancel} className={btnSecondary}>
              Cancel
            </button>
          )}
          <button
            type="button"
            disabled={!text.trim()}
            onClick={review}
            className={btnPrimary}
          >
            Review links
          </button>
        </div>
      </div>
    )
  }

  // ── Step 2: who does each domain go to? ───────
  const assigned = rows.filter((r) => r.recipientId)
  const unassigned = rows.filter((r) => !r.recipientId)

  const draftSummary = [...new Set(assigned.map((r) => r.recipientId))].map(
    (recipientId) => {
      const groupRows = assigned.filter((r) => r.recipientId === recipientId)
      return {
        recipientId,
        domains: groupRows.map((r) => r.domain),
        linkCount: groupRows.reduce((n, r) => n + r.urls.length, 0),
      }
    },
  )

  const createDrafts = () => {
    const groups: DraftGroup[] = draftSummary.map(({ recipientId }) => ({
      recipientId,
      links: assigned
        .filter((r) => r.recipientId === recipientId)
        .flatMap((r) => r.urls.map((url) => ({ url, domain: r.domain }))),
    }))
    state.addLinksAndDrafts(caseId, groups)
    onDone()
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          {rows.length} {rows.length === 1 ? "domain" : "domains"} found. Check
          who each one goes to; you can change any of them.
        </p>
        <button type="button" onClick={() => setRows(null)} className={btnLink}>
          Edit links
        </button>
      </div>

      <div className={`overflow-hidden ${cardClass}`}>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className={thClass}>Domain</th>
              <th className={thClass}>Links</th>
              <th className={thClass}>Send to</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.domain}
                className={`border-b border-slate-100 last:border-0 ${
                  !row.recipientId ? "bg-amber-50/60" : ""
                }`}
              >
                <td className={tdClass}>
                  <p className="font-medium text-slate-900">{row.domain}</p>
                  {!row.known && (
                    <span className="mt-1 inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                      <AlertTriangle className="size-3" />
                      Unknown domain
                    </span>
                  )}
                  <div className="mt-1 space-y-0.5">
                    {row.urls.map((url) => (
                      <p key={url} className="break-all text-xs text-slate-400">
                        {url}
                      </p>
                    ))}
                  </div>
                </td>
                <td className={`${tdClass} text-slate-700`}>
                  {row.urls.length}
                </td>
                <td className={`${tdClass} w-64`}>
                  <select
                    value={row.recipientId}
                    onChange={(e) => setRecipient(row.domain, e.target.value)}
                    aria-label={`Recipient for ${row.domain}`}
                    className={inputBase}
                  >
                    <option value="">Pick a recipient…</option>
                    {state.recipients.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {(invalid.length > 0 || duplicates.length > 0) && (
        <div className="space-y-1 text-xs">
          {invalid.map((u) => (
            <p key={u} className="text-red-600">
              Not a valid link, skipped: {u}
            </p>
          ))}
          {duplicates.map((u) => (
            <p key={u} className="text-slate-500">
              Already in this case, skipped: {u}
            </p>
          ))}
        </div>
      )}

      <div className={`${cardClass} p-4`}>
        <h4 className="text-sm font-medium text-slate-700">
          This will create {draftSummary.length}{" "}
          {draftSummary.length === 1 ? "draft" : "drafts"}
        </h4>
        <ul className="mt-2 space-y-1 text-sm text-slate-600">
          {draftSummary.map((d) => (
            <li key={d.recipientId}>
              <span className="font-medium text-slate-800">
                {recipientName(d.recipientId)}
              </span>
              : {d.domains.join(", ")} ({d.linkCount}{" "}
              {d.linkCount === 1 ? "link" : "links"})
            </li>
          ))}
        </ul>
        {unassigned.length > 0 && (
          <p className="mt-3 text-xs text-amber-700">
            {unassigned.map((r) => r.domain).join(", ")}: no recipient picked,
            so these links will be left out. You can add them to the case later.
          </p>
        )}
      </div>

      <div className="flex justify-end gap-3">
        {onCancel && (
          <button type="button" onClick={onCancel} className={btnSecondary}>
            Cancel
          </button>
        )}
        <button
          type="button"
          disabled={draftSummary.length === 0}
          onClick={createDrafts}
          className={btnPrimary}
        >
          Create drafts
        </button>
      </div>
    </div>
  )
}
