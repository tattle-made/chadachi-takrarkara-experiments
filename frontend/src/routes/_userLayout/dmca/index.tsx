import * as Dialog from "@radix-ui/react-dialog"
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import { Search } from "lucide-react"
import { type FormEvent, useState } from "react"
import {
  btnPrimary,
  btnSecondary,
  cardClass,
  formatDate,
  inputClass,
  labelClass,
  tdClass,
  thClass,
} from "@/preview/components/ui"
import { usePreviewStore } from "@/preview/store"

export const Route = createFileRoute("/_userLayout/dmca/")({
  component: ProfilesPage,
})

function ProfilesPage() {
  const state = usePreviewStore()
  const navigate = useNavigate()
  const [query, setQuery] = useState("")
  const [addOpen, setAddOpen] = useState(false)
  const [fullName, setFullName] = useState("")
  const [notes, setNotes] = useState("")

  const profiles = state.profiles.filter((p) =>
    p.fullName.toLowerCase().includes(query.trim().toLowerCase()),
  )

  const handleOpenChange = (next: boolean) => {
    setAddOpen(next)
    if (!next) {
      setFullName("")
      setNotes("")
    }
  }

  const onCreate = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!fullName.trim()) return
    const id = state.addProfile({ fullName: fullName.trim(), notes })
    handleOpenChange(false)
    navigate({
      to: "/dmca/profiles/$profileId",
      params: { profileId: id },
    })
  }

  return (
    <section>
      <div className="mb-4 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Profiles</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            {state.profiles.length} total
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by name"
              className="w-56 rounded-md border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-1 focus:ring-slate-500"
            />
          </div>
          <Dialog.Root open={addOpen} onOpenChange={handleOpenChange}>
            <Dialog.Trigger asChild>
              <button type="button" className={btnPrimary}>
                New profile
              </button>
            </Dialog.Trigger>
            <Dialog.Portal>
              <Dialog.Overlay className="fixed inset-0 bg-black/30" />
              <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl">
                <Dialog.Title className="mb-4 text-lg font-semibold text-slate-900">
                  New profile
                </Dialog.Title>
                <form onSubmit={onCreate} className="space-y-4">
                  <div>
                    <label htmlFor="fullName" className={labelClass}>
                      Full name
                    </label>
                    <input
                      id="fullName"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      className={inputClass}
                      placeholder="As it should appear in the notice"
                    />
                  </div>
                  <div>
                    <label htmlFor="notes" className={labelClass}>
                      Notes (optional)
                    </label>
                    <textarea
                      id="notes"
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      rows={3}
                      className={inputClass}
                    />
                  </div>
                  <div className="flex justify-end gap-3 pt-2">
                    <Dialog.Close asChild>
                      <button type="button" className={btnSecondary}>
                        Cancel
                      </button>
                    </Dialog.Close>
                    <button
                      type="submit"
                      disabled={!fullName.trim()}
                      className={btnPrimary}
                    >
                      Create profile
                    </button>
                  </div>
                </form>
              </Dialog.Content>
            </Dialog.Portal>
          </Dialog.Root>
        </div>
      </div>

      {profiles.length === 0 ? (
        <p className="text-sm text-slate-400">No profiles match.</p>
      ) : (
        <div className={`overflow-hidden ${cardClass}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className={thClass}>Name</th>
                <th className={thClass}>Cases</th>
                <th className={thClass}>Emails</th>
                <th className={thClass}>Created</th>
              </tr>
            </thead>
            <tbody>
              {profiles.map((p) => {
                const caseIds = state.cases
                  .filter((c) => c.profileId === p.id)
                  .map((c) => c.id)
                const emails = state.emails.filter((e) =>
                  caseIds.includes(e.caseId),
                )
                const sent = emails.filter((e) => e.status === "sent").length
                const drafts = emails.filter((e) => e.status === "draft").length
                const failed = emails.filter(
                  (e) => e.status === "failed",
                ).length
                return (
                  <tr
                    key={p.id}
                    className="border-b border-slate-100 last:border-0 hover:bg-slate-50"
                  >
                    <td className={tdClass}>
                      <Link
                        to="/dmca/profiles/$profileId"
                        params={{ profileId: p.id }}
                        className="font-medium text-slate-900 hover:underline"
                      >
                        {p.fullName}
                      </Link>
                      {p.notes && (
                        <p className="text-xs text-slate-400">{p.notes}</p>
                      )}
                    </td>
                    <td className={`${tdClass} text-slate-700`}>
                      {caseIds.length}
                    </td>
                    <td className={`${tdClass} text-xs text-slate-500`}>
                      {emails.length === 0
                        ? "–"
                        : [
                            sent && `${sent} sent`,
                            drafts && `${drafts} draft`,
                            failed && `${failed} failed`,
                          ]
                            .filter(Boolean)
                            .join(" · ")}
                    </td>
                    <td className={`${tdClass} text-slate-500`}>
                      {formatDate(p.createdAt)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
