import { useState } from "react"
import type { CaseDetail, LinksAdded, TakedownEmail } from "@/dmca/types"
import { btnPrimary, btnSecondary, inputClass } from "@/dmca/ui"
import { useAddLinks } from "@/queries/dmca/profiles.query"
import { ReviewDrafts, seedsFromLinks } from "./ReviewDrafts"

type Props = {
  caseItem: CaseDetail
  emails: TakedownEmail[]
  onClose: () => void
}

/** Paste links → they're saved to the case → review who to email about the
 * new ones → drafts. */
export function AddLinksFlow({ caseItem, emails, onClose }: Props) {
  const [text, setText] = useState("")
  const [result, setResult] = useState<LinksAdded | null>(null)
  const addLinks = useAddLinks(caseItem.id)

  const save = () =>
    addLinks.mutate(text, {
      onSuccess: (added) => {
        setResult(added)
        if (added.added.length + added.skipped.length > 0) setText("")
      },
    })

  // step 2: review the pasted links, new ones and ones the case already had
  const existing = result
    ? caseItem.links.filter((l) => result.skipped.includes(l.url))
    : []
  const toReview = result ? [...result.added, ...existing] : []
  if (toReview.length > 0) {
    return (
      <div className="space-y-4">
        {result && <PasteResult result={result} />}
        <ReviewDrafts
          caseItem={caseItem}
          emails={emails}
          seeds={seedsFromLinks(toReview)}
          onDone={onClose}
          onCancel={onClose}
        />
      </div>
    )
  }

  // step 1: paste
  return (
    <div className="space-y-3">
      <label htmlFor="links" className="text-sm font-medium text-slate-700">
        Paste the links
      </label>
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
        sites are fine; you pick who to email about each site next.
      </p>
      {result && <PasteResult result={result} />}
      <div className="flex justify-end gap-3">
        <button type="button" onClick={onClose} className={btnSecondary}>
          Cancel
        </button>
        <button
          type="button"
          disabled={!text.trim() || addLinks.isPending}
          onClick={save}
          className={btnPrimary}
        >
          {addLinks.isPending ? "Saving…" : "Add links"}
        </button>
      </div>
    </div>
  )
}

/** What happened to the pasted text: added, already in the case, not links. */
function PasteResult({ result }: { result: LinksAdded }) {
  return (
    <div className="space-y-1 text-xs">
      {result.added.length > 0 && (
        <p className="text-slate-600">
          {result.added.length} new{" "}
          {result.added.length === 1 ? "link" : "links"} added to the case.
        </p>
      )}
      {result.skipped.length > 0 && (
        <div className="rounded-md bg-slate-50 px-3 py-2 text-slate-600">
          <p>Already in this case:</p>
          <ul className="my-1 list-disc pl-5">
            {result.skipped.map((u) => (
              <li key={u} className="break-all">
                {u}
              </li>
            ))}
          </ul>
          <p>
            They may already be in other emails (drafts or sent). You can still
            put them in new drafts below. Adding them to a draft that already
            has them won't add them twice.
          </p>
        </div>
      )}
      {result.invalid.map((u) => (
        <p key={u} className="text-red-600">
          Not a link, skipped: {u}
        </p>
      ))}
    </div>
  )
}
