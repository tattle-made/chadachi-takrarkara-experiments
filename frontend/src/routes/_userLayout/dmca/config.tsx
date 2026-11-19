import * as Dialog from "@radix-ui/react-dialog"
import { createFileRoute } from "@tanstack/react-router"
import { Plus, X } from "lucide-react"
import { type FormEvent, useState } from "react"
import { KindBadge } from "@/preview/components/StatusBadge"
import {
  btnPrimary,
  btnSecondary,
  cardClass,
  inputBase,
  inputClass,
  labelClass,
  tdClass,
  thClass,
} from "@/dmca/ui"
import { usePreviewStore } from "@/preview/store"
import { extractDomain } from "@/preview/template"
import type { RecipientKind } from "@/preview/types"

export const Route = createFileRoute("/_userLayout/dmca/config")({
  component: ConfigPage,
})

function ConfigPage() {
  return (
    <div className="space-y-12">
      <RecipientsSection />
      <LegalGroundsSection />
    </div>
  )
}

// ── Recipients + their domains ─────────────────────────────────────────

function RecipientsSection() {
  const state = usePreviewStore()
  const [addOpen, setAddOpen] = useState(false)
  const [name, setName] = useState("")
  const [kind, setKind] = useState<RecipientKind>("platform")
  const [email, setEmail] = useState("")
  const [domainInputs, setDomainInputs] = useState<Record<string, string>>({})
  const [domainErrors, setDomainErrors] = useState<Record<string, string>>({})

  const handleOpenChange = (next: boolean) => {
    setAddOpen(next)
    if (!next) {
      setName("")
      setKind("platform")
      setEmail("")
    }
  }

  const onCreate = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!name.trim() || !email.trim()) return
    state.addRecipient({ name: name.trim(), kind, email: email.trim() })
    handleOpenChange(false)
  }

  const addDomain = (recipientId: string) => {
    const domain = extractDomain(domainInputs[recipientId] ?? "")
    if (!domain) {
      setDomainErrors((e) => ({ ...e, [recipientId]: "Not a valid domain" }))
      return
    }
    state.addDomain(domain, recipientId)
    setDomainInputs((d) => ({ ...d, [recipientId]: "" }))
  }

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Recipients</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Who takedown emails can go to. When a pasted link is on one of a
            recipient's domains, that recipient is pre-filled; counsellors can
            still pick any other.
          </p>
        </div>
        <Dialog.Root open={addOpen} onOpenChange={handleOpenChange}>
          <Dialog.Trigger asChild>
            <button type="button" className={btnPrimary}>
              Add recipient
            </button>
          </Dialog.Trigger>
          <Dialog.Portal>
            <Dialog.Overlay className="fixed inset-0 bg-black/30" />
            <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl">
              <Dialog.Title className="mb-4 text-lg font-semibold text-slate-900">
                Add recipient
              </Dialog.Title>
              <form onSubmit={onCreate} className="space-y-4">
                <div>
                  <label htmlFor="rName" className={labelClass}>
                    Name
                  </label>
                  <input
                    id="rName"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Cloudflare"
                    className={inputClass}
                  />
                </div>
                <div>
                  <label htmlFor="rKind" className={labelClass}>
                    Type
                  </label>
                  <select
                    id="rKind"
                    value={kind}
                    onChange={(e) => setKind(e.target.value as RecipientKind)}
                    className={inputClass}
                  >
                    <option value="platform">Platform (the site itself)</option>
                    <option value="service_provider">
                      Service provider (e.g. Cloudflare, a host)
                    </option>
                  </select>
                </div>
                <div>
                  <label htmlFor="rEmail" className={labelClass}>
                    Takedown email address
                  </label>
                  <input
                    id="rEmail"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="abuse@example.com"
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
                    disabled={!name.trim() || !email.trim()}
                    className={btnPrimary}
                  >
                    Add recipient
                  </button>
                </div>
              </form>
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>
      </div>

      <div className={`overflow-hidden ${cardClass}`}>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className={thClass}>Recipient</th>
              <th className={thClass}>Email</th>
              <th className={thClass}>Domains</th>
            </tr>
          </thead>
          <tbody>
            {state.recipients.map((r) => {
              const rows = state.domains.filter((d) => d.recipientId === r.id)
              return (
                <tr
                  key={r.id}
                  className="border-b border-slate-100 last:border-0"
                >
                  <td className={tdClass}>
                    <p className="font-medium text-slate-900">{r.name}</p>
                    <div className="mt-1">
                      <KindBadge kind={r.kind} />
                    </div>
                  </td>
                  <td className={`${tdClass} text-slate-700`}>
                    {r.emails.join(", ")}
                  </td>
                  <td className={tdClass}>
                    <div className="flex flex-wrap gap-1.5">
                      {rows.map((dr) => (
                        <span
                          key={dr.domain}
                          className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 py-0.5 pl-2 pr-1 text-xs text-slate-700"
                        >
                          {dr.domain}
                          <button
                            type="button"
                            aria-label={`Remove ${dr.domain}`}
                            onClick={() => state.removeDomain(dr.domain)}
                            className="text-slate-400 hover:text-red-600"
                          >
                            <X className="size-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                    <form
                      onSubmit={(e) => {
                        e.preventDefault()
                        addDomain(r.id)
                      }}
                      className="mt-2 flex gap-2"
                    >
                      <input
                        value={domainInputs[r.id] ?? ""}
                        onChange={(e) => {
                          setDomainInputs((d) => ({
                            ...d,
                            [r.id]: e.target.value,
                          }))
                          setDomainErrors((er) => ({ ...er, [r.id]: "" }))
                        }}
                        placeholder="add domain, e.g. mirror-site.com"
                        className={`${inputBase} py-1 text-xs`}
                      />
                      <button
                        type="submit"
                        aria-label="Add domain"
                        disabled={!domainInputs[r.id]?.trim()}
                        className="rounded-md border border-slate-200 px-2 text-slate-500 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        <Plus className="size-4" />
                      </button>
                    </form>
                    {domainErrors[r.id] && (
                      <p className="mt-1 text-xs text-red-600">
                        {domainErrors[r.id]}
                      </p>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}

// ── Legal grounds ──────────────────────────────────────────────────────

function LegalGroundsSection() {
  const state = usePreviewStore()

  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Legal grounds
          </h2>
          <p className="mt-0.5 text-sm text-slate-500">
            Standard clauses counsellors can tick on each draft. Placeholder
            wording for now.
          </p>
        </div>
        <button
          type="button"
          onClick={() =>
            state.addLegalGround({
              title: "New legal ground",
              citation: "",
              clauseText: "",
              defaultSelected: false,
              active: true,
            })
          }
          className={`${btnSecondary} inline-flex items-center gap-2`}
        >
          <Plus className="size-4" />
          Add
        </button>
      </div>

      <div className="space-y-3">
        {state.legalGrounds.map((g) => (
          <div
            key={g.id}
            className={`${cardClass} space-y-3 p-4 ${g.active ? "" : "opacity-60"}`}
          >
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                value={g.title}
                onChange={(e) =>
                  state.updateLegalGround(g.id, { title: e.target.value })
                }
                placeholder="Title"
                className={`${inputBase} font-medium`}
              />
              <input
                value={g.citation}
                onChange={(e) =>
                  state.updateLegalGround(g.id, { citation: e.target.value })
                }
                placeholder="Citation, e.g. IT Rules 2021, Rule 3(2)(b)"
                className={inputBase}
              />
            </div>
            <textarea
              value={g.clauseText}
              onChange={(e) =>
                state.updateLegalGround(g.id, { clauseText: e.target.value })
              }
              rows={2}
              placeholder="Text that appears in the email"
              className={inputBase}
            />
            <div className="flex gap-6 text-sm text-slate-600">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={g.defaultSelected}
                  onChange={() =>
                    state.updateLegalGround(g.id, {
                      defaultSelected: !g.defaultSelected,
                    })
                  }
                />
                Ticked by default on new drafts
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={g.active}
                  onChange={() =>
                    state.updateLegalGround(g.id, { active: !g.active })
                  }
                />
                Active
              </label>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
