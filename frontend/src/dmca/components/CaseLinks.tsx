import { Plus, X } from "lucide-react"
import type { CaseDetail, CaseLink, TakedownEmail } from "@/dmca/types"
import { btnPrimary, btnSecondary, cardClass } from "@/dmca/ui"
import { useDeleteLink } from "@/queries/dmca/profiles.query"
import { seedsFromLinks } from "./ReviewDrafts"

type Props = {
  caseItem: CaseDetail
  emails: TakedownEmail[]
  onAdd: () => void
  // open the review for links that aren't in any email yet
  onDraft: (links: CaseLink[]) => void
}

/** The case's links by site, with how many emails each is in. */
export function CaseLinks({ caseItem, emails, onAdd, onDraft }: Props) {
  const deleteLink = useDeleteLink(caseItem.id)
  const emailsWith = (link: CaseLink) =>
    emails.filter((e) => e.links.some((l) => l.id === link.id))
  // a link in an email that's gone out (or is going) stays, as its record
  const isLocked = (link: CaseLink) =>
    emailsWith(link).some((e) => e.status !== "draft")
  const notEmailed = caseItem.links.filter((l) => emailsWith(l).length === 0)

  const remove = (link: CaseLink) => {
    if (
      window.confirm(
        `Remove ${link.url} from the case? It's also taken out of any drafts.`,
      )
    ) {
      deleteLink.mutate(link.id)
    }
  }

  return (
    <section>
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-slate-900">
          Links ({caseItem.links.length})
        </h2>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={notEmailed.length === 0}
            onClick={() => onDraft(notEmailed)}
            className={btnSecondary}
          >
            Draft emails ({notEmailed.length} not emailed yet)
          </button>
          <button
            type="button"
            onClick={onAdd}
            className={`${btnPrimary} inline-flex items-center gap-2`}
          >
            <Plus className="size-4" />
            Add links
          </button>
        </div>
      </div>

      {caseItem.links.length === 0 ? (
        <p className="text-sm text-slate-400">
          No links yet. Add the links to take down.
        </p>
      ) : (
        <div className={`${cardClass} divide-y divide-slate-100`}>
          {seedsFromLinks(caseItem.links).map(({ domain, links }) => (
            <div key={domain} className="px-4 py-3">
              <p className="text-sm font-medium text-slate-900">{domain}</p>
              <ul className="mt-1 space-y-0.5">
                {links.map((link) => {
                  const count = emailsWith(link).length
                  return (
                    <li
                      key={link.id}
                      className="flex items-center gap-2 text-xs"
                    >
                      <span className="break-all text-slate-500">
                        {link.url}
                      </span>
                      <span
                        className={count ? "text-slate-400" : "text-amber-700"}
                      >
                        {count
                          ? `in ${count} ${count === 1 ? "email" : "emails"}`
                          : "not emailed yet"}
                      </span>
                      {!isLocked(link) && (
                        <button
                          type="button"
                          onClick={() => remove(link)}
                          aria-label={`Remove ${link.url}`}
                          className="text-slate-300 hover:text-red-600"
                        >
                          <X className="size-3.5" />
                        </button>
                      )}
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
