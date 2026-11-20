import * as Dialog from "@radix-ui/react-dialog"
import { useQuery } from "@tanstack/react-query"
import { Info, Plus, X } from "lucide-react"
import { type FormEvent, type ReactNode, useState } from "react"
import { EMAIL_TYPE_LABELS, RELATION_LABELS } from "@/dmca/labels"
import type { DomainRelation, EmailType, Recipient } from "@/dmca/types"
import {
  btnLink,
  btnPrimary,
  btnSecondary,
  cardClass,
  fieldBase,
  inputBase,
  inputClass,
  labelClass,
} from "@/dmca/ui"
import {
  recipientsQueryOptions,
  useAddRecipientDomain,
  useAddRecipientEmail,
  useCreateRecipient,
  useDeleteRecipient,
  useDeleteRecipientDomain,
  useDeleteRecipientEmail,
  useUpdateRecipient,
} from "@/queries/dmca/config.query"

const EMAIL_TYPES = Object.keys(EMAIL_TYPE_LABELS) as EmailType[]
// also the order we email a site's organisations in
const RELATIONS = Object.keys(RELATION_LABELS) as DomainRelation[]

// one colour per address type, so they're told apart at a glance
const TYPE_BADGE: Record<EmailType, string> = {
  dmca: "bg-blue-100 text-blue-800",
  abuse: "bg-amber-100 text-amber-800",
  csam: "bg-rose-100 text-rose-800",
  general: "bg-slate-200 text-slate-800",
}

/** "https://www.Site.com/a" -> "site.com", the way pasted links are read. */
const cleanDomain = (raw: string) => {
  const text = raw.trim()
  try {
    const url = new URL(/^[a-z]+:\/\//i.test(text) ? text : `https://${text}`)
    return url.hostname.replace(/^www\./, "")
  } catch {
    return text.toLowerCase()
  }
}

type View = "organisations" | "sites"

/** Config's recipients: how it works, search, and two views of the same data
 * (organisations with their addresses; sites with who to email, in order). */
export function RecipientsConfig() {
  const { data, isPending } = useQuery(recipientsQueryOptions())
  const [search, setSearch] = useState("")
  const [view, setView] = useState<View>("organisations")
  const all = data?.data ?? []
  const q = search.trim().toLowerCase()

  return (
    <section>
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Who we email
          </h2>
          <p className="mt-0.5 text-sm text-slate-600">
            Organisations, their email addresses, and which sites they're
            emailed about.
          </p>
        </div>
        <RecipientFormDialog
          trigger={
            <button
              type="button"
              className={`${btnPrimary} inline-flex items-center gap-2`}
            >
              <Plus className="size-4" />
              New organisation
            </button>
          }
        />
      </div>

      <HowItWorks />

      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex rounded-md border border-slate-200 bg-white p-1 text-sm">
          {(["organisations", "sites"] as View[]).map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => setView(v)}
              className={`rounded px-3 py-1 ${
                view === v
                  ? "bg-slate-900 font-medium text-white"
                  : "text-slate-700 hover:bg-slate-100"
              }`}
            >
              {v === "organisations" ? "Organisations" : "By site"}
            </button>
          ))}
        </div>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={
            view === "organisations"
              ? "Search name, address or site"
              : "Search site or organisation"
          }
          className={`${fieldBase} w-64`}
        />
      </div>

      {isPending ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : view === "organisations" ? (
        <Organisations recipients={all} q={q} />
      ) : (
        <BySite recipients={all} q={q} />
      )}
    </section>
  )
}

/** The two rules the review screen and Escalate follow, in plain words. */
function HowItWorks() {
  return (
    <div className="mb-5 flex gap-3 rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-slate-800">
      <Info className="mt-0.5 size-4 shrink-0 text-sky-700" />
      <div className="space-y-3">
        <p className="font-semibold text-slate-900">How it works</p>
        <div>
          <p className="font-medium text-slate-900">
            1. Every site has a list of organisations to email, in this order:
          </p>
          <p className="mt-0.5">
            Website owner → CDN (e.g. Cloudflare) → Host → Registrar
          </p>
          <p className="mt-0.5 text-slate-600">
            A new email suggests the first one on the list. Escalate suggests
            the next one.
          </p>
        </div>
        <div>
          <p className="font-medium text-slate-900">
            2. Every organisation has one or more email addresses, each marked
            with a type:
          </p>
          <p className="mt-0.5">
            We use its DMCA address if it has one, otherwise Abuse, otherwise
            General. On minor cases, CSAM comes first.
          </p>
        </div>
        <p className="rounded-md bg-white/70 px-3 py-2 font-medium text-slate-900">
          Both are only suggestions. On every draft, the counsellor can pick any
          organisation and any of its email addresses, and change them at any
          time before sending.
        </p>
      </div>
    </div>
  )
}

/** An address type as a coloured tag. */
function TypeBadge({ type }: { type: EmailType }) {
  return (
    <span
      className={`inline-block w-16 shrink-0 rounded px-1.5 py-0.5 text-center text-xs font-medium ${TYPE_BADGE[type]}`}
    >
      {EMAIL_TYPE_LABELS[type]}
    </span>
  )
}

/** The small × that removes an address or a site link. */
function RemoveButton({
  label,
  onClick,
}: {
  label: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`Remove ${label}`}
      className="text-slate-400 hover:text-red-600"
    >
      <X className="size-4" />
    </button>
  )
}

// --- organisations ---

/** One card per organisation, filtered by name, address or site. */
function Organisations({
  recipients,
  q,
}: {
  recipients: Recipient[]
  q: string
}) {
  const shown = recipients.filter(
    (r) =>
      !q ||
      r.name.toLowerCase().includes(q) ||
      r.emails.some((e) => e.address.toLowerCase().includes(q)) ||
      r.domain_links.some((l) => l.domain.domain.includes(q)),
  )
  if (shown.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        {q ? "Nothing matches." : "No organisations yet."}
      </p>
    )
  }
  return (
    <div className="space-y-4">
      {shown.map((r) => (
        <OrganisationCard key={r.id} recipient={r} />
      ))}
    </div>
  )
}

/** One organisation: its email addresses, and the sites we email it about. */
function OrganisationCard({ recipient }: { recipient: Recipient }) {
  const deleteRecipient = useDeleteRecipient()
  const deleteEmail = useDeleteRecipientEmail()
  const deleteDomain = useDeleteRecipientDomain()

  const onDelete = () => {
    if (
      window.confirm(
        `Delete ${recipient.name}, with its email addresses and sites? Emails already made to it stay.`,
      )
    ) {
      deleteRecipient.mutate(recipient.id)
    }
  }

  return (
    <div className={`${cardClass} p-5`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-base font-semibold text-slate-900">
            {recipient.name}
          </p>
          {recipient.notes && (
            <p className="mt-0.5 text-sm text-slate-600">{recipient.notes}</p>
          )}
        </div>
        <div className="flex gap-3">
          <RecipientFormDialog
            recipient={recipient}
            trigger={
              <button type="button" className={btnLink}>
                Edit
              </button>
            }
          />
          <button
            type="button"
            onClick={onDelete}
            className={`${btnLink} hover:text-red-600`}
          >
            Delete
          </button>
        </div>
      </div>

      <div className="mt-4">
        <p className="text-sm font-semibold text-slate-800">Email addresses</p>
        {recipient.emails.length === 0 ? (
          <p className="mt-1 text-sm text-amber-700">
            No email address yet, so emails to {recipient.name} can't be sent.
          </p>
        ) : (
          <ul className="mt-2 space-y-1.5">
            {recipient.emails.map((e) => (
              <li key={e.id} className="flex items-center gap-3 text-sm">
                <TypeBadge type={e.email_type} />
                <span className="break-all text-slate-900">{e.address}</span>
                <RemoveButton
                  label={e.address}
                  onClick={() =>
                    deleteEmail.mutate({
                      recipientId: recipient.id,
                      emailId: e.id,
                    })
                  }
                />
              </li>
            ))}
          </ul>
        )}
        <AddEmail recipientId={recipient.id} />
      </div>

      <div className="mt-5 border-t border-slate-200 pt-4">
        <p className="text-sm font-semibold text-slate-800">Sites</p>
        <p className="text-sm text-slate-600">
          The sites we email {recipient.name} about, and what it is to each
          site.
        </p>
        {recipient.domain_links.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No sites yet.</p>
        ) : (
          <ul className="mt-2 space-y-1.5">
            {recipient.domain_links.map((l) => (
              <li key={l.id} className="flex items-center gap-2 text-sm">
                <span className="font-medium text-slate-900">
                  {l.domain.domain}
                </span>
                <span className="text-slate-600">
                  — {recipient.name} is its{" "}
                  <span className="font-medium text-slate-800">
                    {RELATION_LABELS[l.relation]}
                  </span>
                </span>
                <RemoveButton
                  label={l.domain.domain}
                  onClick={() =>
                    deleteDomain.mutate({
                      recipientId: recipient.id,
                      linkId: l.id,
                    })
                  }
                />
              </li>
            ))}
          </ul>
        )}
        <AddDomain recipient={recipient} />
      </div>
    </div>
  )
}

/** Inline row: "[type] [address] Add". */
function AddEmail({ recipientId }: { recipientId: string }) {
  const [address, setAddress] = useState("")
  const [type, setType] = useState<EmailType>("dmca")
  const add = useAddRecipientEmail()

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!address.trim()) return
    add.mutate(
      { recipientId, address: address.trim(), email_type: type },
      { onSuccess: () => setAddress("") },
    )
  }

  return (
    <form onSubmit={onSubmit} className="mt-3 flex max-w-xl gap-2">
      <select
        value={type}
        onChange={(e) => setType(e.target.value as EmailType)}
        aria-label="Address type"
        className={`${fieldBase} py-1.5`}
      >
        {EMAIL_TYPES.map((t) => (
          <option key={t} value={t}>
            {EMAIL_TYPE_LABELS[t]}
          </option>
        ))}
      </select>
      <input
        type="email"
        value={address}
        onChange={(e) => setAddress(e.target.value)}
        placeholder="Add an email address"
        aria-label="New email address"
        className={`${fieldBase} min-w-0 flex-1 py-1.5`}
      />
      <button
        type="submit"
        disabled={!address.trim() || add.isPending}
        className={`${btnSecondary} py-1.5`}
      >
        Add
      </button>
    </form>
  )
}

/** Inline row on an organisation card: "[site] — <name> is its [role] Add". */
function AddDomain({ recipient }: { recipient: Recipient }) {
  const [domain, setDomain] = useState("")
  const [relation, setRelation] = useState<DomainRelation>("website_owner")
  const add = useAddRecipientDomain()

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!domain.trim()) return
    add.mutate(
      { recipientId: recipient.id, domain: cleanDomain(domain), relation },
      { onSuccess: () => setDomain("") },
    )
  }

  return (
    <form
      onSubmit={onSubmit}
      className="mt-3 flex max-w-2xl flex-wrap items-center gap-2 text-sm"
    >
      <input
        value={domain}
        onChange={(e) => setDomain(e.target.value)}
        placeholder="Add a site, e.g. site.com"
        aria-label="New site"
        className={`${fieldBase} min-w-0 flex-1 py-1.5`}
      />
      <span className="text-slate-700">— {recipient.name} is its</span>
      <RelationSelect value={relation} onChange={setRelation} />
      <button
        type="submit"
        disabled={!domain.trim() || add.isPending}
        className={`${btnSecondary} py-1.5`}
      >
        Add
      </button>
    </form>
  )
}

// --- by site ---

type SiteLink = {
  linkId: string
  relation: DomainRelation
  recipient: Recipient
}

/** One card per site, showing who we email about it, in order. */
function BySite({ recipients, q }: { recipients: Recipient[]; q: string }) {
  // regroup the organisations' site links by site
  const bySite = new Map<string, SiteLink[]>()
  for (const recipient of recipients) {
    for (const l of recipient.domain_links) {
      const links = bySite.get(l.domain.domain) ?? []
      links.push({ linkId: l.id, relation: l.relation, recipient })
      bySite.set(l.domain.domain, links)
    }
  }
  const sites = [...bySite]
    .filter(
      ([site, links]) =>
        !q ||
        site.includes(q) ||
        links.some((l) => l.recipient.name.toLowerCase().includes(q)),
    )
    .sort(([a], [b]) => a.localeCompare(b))

  return (
    <div className="space-y-4">
      <AddSite recipients={recipients} />
      {sites.length === 0 ? (
        <p className="text-sm text-slate-500">
          {q ? "No site matches." : "No sites yet."}
        </p>
      ) : (
        sites.map(([site, links]) => (
          <SiteCard
            key={site}
            site={site}
            links={links}
            recipients={recipients}
          />
        ))
      )}
    </div>
  )
}

/** One site: Website owner → CDN → Host → Registrar, with each organisation
 * and its email addresses. */
function SiteCard({
  site,
  links,
  recipients,
}: {
  site: string
  links: SiteLink[]
  recipients: Recipient[]
}) {
  const deleteDomain = useDeleteRecipientDomain()

  return (
    <div className={`${cardClass} p-5`}>
      <p className="text-base font-semibold text-slate-900">{site}</p>
      <p className="mb-3 text-sm text-slate-600">
        Who we email about this site, in order.
      </p>
      <ol className="divide-y divide-slate-100">
        {RELATIONS.map((relation, i) => {
          const inRole = links.filter((l) => l.relation === relation)
          return (
            <li key={relation} className="flex items-start gap-4 py-2 text-sm">
              <span className="w-32 shrink-0 font-medium text-slate-700">
                {i + 1}. {RELATION_LABELS[relation]}
              </span>
              {inRole.length === 0 ? (
                <span className="text-slate-400">Nobody yet</span>
              ) : (
                <div className="flex-1 space-y-2">
                  {inRole.map((l) => (
                    <div key={l.linkId}>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-900">
                          {l.recipient.name}
                        </span>
                        <RemoveButton
                          label={`${l.recipient.name} from ${site}`}
                          onClick={() =>
                            deleteDomain.mutate({
                              recipientId: l.recipient.id,
                              linkId: l.linkId,
                            })
                          }
                        />
                      </div>
                      {l.recipient.emails.length === 0 ? (
                        <p className="text-amber-700">No email address yet</p>
                      ) : (
                        <ul className="mt-1 space-y-1">
                          {l.recipient.emails.map((e) => (
                            <li key={e.id} className="flex items-center gap-2">
                              <TypeBadge type={e.email_type} />
                              <span className="break-all text-slate-800">
                                {e.address}
                              </span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </li>
          )
        })}
      </ol>
      <div className="mt-2 border-t border-slate-200 pt-3">
        <LinkRecipient site={site} recipients={recipients} />
      </div>
    </div>
  )
}

/** Inline row on a site card: "Add [organisation] as [role] Add". */
function LinkRecipient({
  site,
  recipients,
}: {
  site: string
  recipients: Recipient[]
}) {
  const [recipientId, setRecipientId] = useState("")
  const [relation, setRelation] = useState<DomainRelation>("website_owner")
  const add = useAddRecipientDomain()

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!recipientId) return
    add.mutate(
      { recipientId, domain: site, relation },
      { onSuccess: () => setRecipientId("") },
    )
  }

  return (
    <form
      onSubmit={onSubmit}
      className="flex max-w-xl flex-wrap items-center gap-2 text-sm"
    >
      <span className="text-slate-700">Add</span>
      <RecipientSelect
        value={recipientId}
        onChange={setRecipientId}
        recipients={recipients}
      />
      <span className="text-slate-700">as</span>
      <RelationSelect value={relation} onChange={setRelation} />
      <button
        type="submit"
        disabled={!recipientId || add.isPending}
        className={`${btnSecondary} py-1.5`}
      >
        Add
      </button>
    </form>
  )
}

/** Top of the By site view: "New site [site]: [organisation] as [role] Add". */
function AddSite({ recipients }: { recipients: Recipient[] }) {
  const [domain, setDomain] = useState("")
  const [recipientId, setRecipientId] = useState("")
  const [relation, setRelation] = useState<DomainRelation>("website_owner")
  const add = useAddRecipientDomain()

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!domain.trim() || !recipientId) return
    add.mutate(
      { recipientId, domain: cleanDomain(domain), relation },
      {
        onSuccess: () => {
          setDomain("")
          setRecipientId("")
        },
      },
    )
  }

  return (
    <form
      onSubmit={onSubmit}
      className={`${cardClass} flex flex-wrap items-center gap-2 p-4 text-sm`}
    >
      <span className="font-semibold text-slate-800">New site</span>
      <input
        value={domain}
        onChange={(e) => setDomain(e.target.value)}
        placeholder="site.com"
        aria-label="Site"
        className={`${fieldBase} w-48 py-1.5`}
      />
      <span className="text-slate-700">email</span>
      <RecipientSelect
        value={recipientId}
        onChange={setRecipientId}
        recipients={recipients}
      />
      <span className="text-slate-700">as</span>
      <RelationSelect value={relation} onChange={setRelation} />
      <button
        type="submit"
        disabled={!domain.trim() || !recipientId || add.isPending}
        className={`${btnSecondary} py-1.5`}
      >
        Add
      </button>
    </form>
  )
}

/** The role dropdown: Website owner / CDN / Host / Registrar. */
function RelationSelect({
  value,
  onChange,
}: {
  value: DomainRelation
  onChange: (relation: DomainRelation) => void
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as DomainRelation)}
      aria-label="Role"
      className={`${fieldBase} py-1.5`}
    >
      {RELATIONS.map((r) => (
        <option key={r} value={r}>
          {RELATION_LABELS[r]}
        </option>
      ))}
    </select>
  )
}

/** A dropdown of every organisation. */
function RecipientSelect({
  value,
  onChange,
  recipients,
}: {
  value: string
  onChange: (id: string) => void
  recipients: Recipient[]
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      aria-label="Organisation"
      className={`${fieldBase} py-1.5`}
    >
      <option value="">Pick an organisation…</option>
      {recipients.map((r) => (
        <option key={r.id} value={r.id}>
          {r.name}
        </option>
      ))}
    </select>
  )
}

/** Create an organisation (a recipient), or edit its name and notes. */
function RecipientFormDialog({
  trigger,
  recipient,
}: {
  trigger: ReactNode
  // edit this one; leave out to create a new one
  recipient?: Recipient
}) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [notes, setNotes] = useState("")
  const create = useCreateRecipient()
  const update = useUpdateRecipient()
  const saving = create.isPending || update.isPending

  const handleOpenChange = (next: boolean) => {
    setOpen(next)
    if (next) {
      setName(recipient?.name ?? "")
      setNotes(recipient?.notes ?? "")
    }
  }

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!name.trim()) return
    const input = { name: name.trim(), notes: notes.trim() || null }
    const done = { onSuccess: () => setOpen(false) }
    if (recipient) update.mutate({ id: recipient.id, ...input }, done)
    else create.mutate(input, done)
  }

  return (
    <Dialog.Root open={open} onOpenChange={handleOpenChange}>
      <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/30" />
        <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl">
          <Dialog.Title className="mb-4 text-lg font-semibold text-slate-900">
            {recipient ? "Edit organisation" : "New organisation"}
          </Dialog.Title>
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label htmlFor="recipientName" className={labelClass}>
                Name
              </label>
              <input
                id="recipientName"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Cloudflare"
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="recipientNotes" className={labelClass}>
                Notes (optional)
              </label>
              <textarea
                id="recipientNotes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                className={`mt-1 ${inputBase}`}
              />
            </div>
            {!recipient && (
              <p className="text-xs text-slate-500">
                Add its email addresses on its card after saving, and link it to
                sites in the By site view.
              </p>
            )}
            <div className="flex justify-end gap-3 pt-2">
              <Dialog.Close asChild>
                <button type="button" className={btnSecondary}>
                  Cancel
                </button>
              </Dialog.Close>
              <button
                type="submit"
                disabled={!name.trim() || saving}
                className={btnPrimary}
              >
                {saving ? "Saving…" : recipient ? "Save" : "Add organisation"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
