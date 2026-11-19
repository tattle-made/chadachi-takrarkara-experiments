import { useQuery } from "@tanstack/react-query"
import { AlertTriangle } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"
import { EMAIL_TYPE_LABELS, RELATION_LABELS } from "@/dmca/labels"
import type {
  CaseDetail,
  CaseLink,
  DomainRelation,
  DomainResolved,
  DraftItem,
  EmailType,
  Recipient,
  TakedownEmail,
} from "@/dmca/types"
import {
  btnPrimary,
  btnSecondary,
  cardClass,
  inputBase,
  tdClass,
  thClass,
} from "@/dmca/ui"
import {
  recipientsQueryOptions,
  resolveDomainsQueryOptions,
} from "@/queries/dmca/config.query"
import {
  escalationQueryOptions,
  useCreateDrafts,
} from "@/queries/dmca/emails.query"

// Rati's escalation order; a site's first recipient in it is pre-filled
const RELATION_ORDER: DomainRelation[] = [
  "website_owner",
  "cdn",
  "host",
  "registrar",
]
// the address type picked by default, as the backend does
const ADULT_TYPES: EmailType[] = ["dmca", "abuse", "general"]
const MINOR_TYPES: EmailType[] = ["csam", "dmca", "abuse", "general"]
const TYPE_ORDER: EmailType[] = ["dmca", "abuse", "csam", "general"]

/** A site and the links to email about it, optionally with who to send to
 * (Escalate fills it in; null = nobody suggested). */
export type ReviewSeed = {
  domain: string
  links: CaseLink[]
  recipientId?: string | null
  relation?: DomainRelation | null
}

/** One review row per site, from a list of links. groups links by site and makes one "seed" per site.  */
export function seedsFromLinks(links: CaseLink[]): ReviewSeed[] {
  const byDomain = new Map<string, CaseLink[]>()
  for (const link of links) {
    byDomain.set(link.domain, [...(byDomain.get(link.domain) ?? []), link])
  }
  return [...byDomain].map(([domain, links]) => ({ domain, links }))
}

type Props = {
  caseItem: CaseDetail
  // the case's emails, to offer "add to existing draft"
  emails: TakedownEmail[]
  seeds: ReviewSeed[]
  onDone: () => void
  onCancel: () => void
}

/** The review screen: who to email about each site, then "Create drafts".
 * Waits for Config's recipients before showing the rows. */
export function ReviewDrafts(props: Props) {
  const domains = props.seeds.map((s) => s.domain)
  const resolved = useQuery(resolveDomainsQueryOptions(domains))
  const recipients = useQuery(recipientsQueryOptions())

  if (props.seeds.length === 0) {
    return <p className="text-sm text-slate-400">No links to email.</p>
  }
  if (resolved.isPending || recipients.isPending) {
    return <p className="text-sm text-slate-400">Loading recipients…</p>
  }
  if (!resolved.data || !recipients.data) {
    return <p className="text-sm text-red-600">Couldn't load the recipients.</p>
  }
  return (
    <ReviewTable
      {...props}
      resolved={resolved.data}
      recipients={recipients.data.data}
    />
  )
}

/** Escalate on a sent email: the review screen pre-filled with the next
 * recipient for each site, and that email's links. */
export function EscalationReview({
  emailId,
  ...props
}: Omit<Props, "seeds"> & { emailId: string }) {
  const { data: suggestions, isPending } = useQuery(
    escalationQueryOptions(emailId),
  )
  const email = props.emails.find((e) => e.id === emailId)

  if (isPending) {
    return <p className="text-sm text-slate-400">Loading suggestions…</p>
  }
  if (!email || !suggestions) {
    return <p className="text-sm text-red-600">Couldn't load that email.</p>
  }
  const seeds = suggestions
    .map((s) => ({
      domain: s.domain,
      links: email.links.filter(
        (l) => l.domain === s.domain && l.removed_at === null,
      ),
      recipientId: s.recipient_id,
      relation: s.relation,
    }))
    .filter((s) => s.links.length > 0)

  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-500">
        Escalating the email to{" "}
        <span className="font-medium text-slate-800">
          {email.recipient_name}
        </span>
        . The next one in line is filled in for each site; change any of them.
      </p>
      <ReviewDrafts {...props} seeds={seeds} />
    </div>
  )
}

type Row = {
  domain: string
  links: CaseLink[]
  // the site is in Config (has recipients linked)
  known: boolean
  recipientId: string // "" = none picked yet
  relation: DomainRelation | null
  emailType: EmailType | null
  addTo: string // "" = new email, else the id of a draft to add to
}

type TableProps = Props & {
  resolved: DomainResolved[]
  recipients: Recipient[]
}

function ReviewTable({
  caseItem,
  emails,
  seeds,
  resolved,
  recipients,
  onDone,
  onCancel,
}: TableProps) {
  const createDrafts = useCreateDrafts(caseItem.id)
  const isMinor = caseItem.is_minor

  const siteOf = (domain: string) =>
    resolved.find((s) => s.domain === domain)?.recipient_links ?? []
  const recipientOf = (id: string) => recipients.find((r) => r.id === id)
  // this case's drafts to the same recipient and address type
  const draftsTo = (recipientId: string, emailType: EmailType | null) =>
    emails.filter(
      (e) =>
        e.status === "draft" &&
        e.recipient_id === recipientId &&
        e.email_type === emailType,
    )
  // add to an unedited draft if there is one (adding resets an edited body)
  const defaultDraft = (recipientId: string, emailType: EmailType | null) =>
    draftsTo(recipientId, emailType).find((d) => !d.is_body_custom)?.id ?? ""

  /** Set a row's recipient, and the address type and draft that go with it. */
  const withRecipient = (
    row: Row,
    recipientId: string,
    relation: DomainRelation | null,
  ): Row => {
    const types = typesOf(recipientOf(recipientId))
    const emailType =
      (isMinor ? MINOR_TYPES : ADULT_TYPES).find((t) => types.includes(t)) ??
      null
    return {
      ...row,
      recipientId,
      relation,
      emailType,
      addTo: defaultDraft(recipientId, emailType),
    }
  }

  const [rows, setRows] = useState<Row[]>(() =>
    seeds.map((seed) => {
      const site = siteOf(seed.domain)
      const base: Row = {
        domain: seed.domain,
        links: seed.links,
        known: site.length > 0,
        recipientId: "",
        relation: null,
        emailType: null,
        addTo: "",
      }
      if (seed.recipientId !== undefined) {
        return seed.recipientId
          ? withRecipient(base, seed.recipientId, seed.relation ?? null)
          : base
      }
      const first = RELATION_ORDER.map((rel) =>
        site.find((l) => l.relation === rel),
      ).find(Boolean)
      return first
        ? withRecipient(base, first.recipient.id, first.relation)
        : base
    }),
  )

  const update = (domain: string, change: (row: Row) => Row) =>
    setRows((rs) => rs.map((r) => (r.domain === domain ? change(r) : r)))

  const pickRecipient = (row: Row, recipientId: string) => {
    // the recipient's role for this site, if it has one
    const relation =
      siteOf(row.domain).find((l) => l.recipient.id === recipientId)
        ?.relation ?? null
    update(row.domain, (r) => withRecipient(r, recipientId, relation))
  }

  const ready = rows.filter((r) => r.recipientId)
  const skipped = rows.filter((r) => !r.recipientId)
  const newEmails = new Set(
    ready.filter((r) => !r.addTo).map((r) => `${r.recipientId}|${r.emailType}`),
  ).size
  const addedTo = new Set(ready.filter((r) => r.addTo).map((r) => r.addTo)).size

  const submit = () => {
    const items: DraftItem[] = ready.map((r) => ({
      domain: r.domain,
      link_ids: r.links.map((l) => l.id),
      recipient_id: r.recipientId,
      email_type: r.emailType,
      relation: r.relation,
      add_to_email_id: r.addTo || null,
    }))
    createDrafts.mutate(items, {
      onSuccess: ({ created, updated }) => {
        toast.success(
          [
            created.length && `${created.length} drafts created`,
            updated.length && `${updated.length} drafts updated`,
          ]
            .filter(Boolean)
            .join(", "),
        )
        onDone()
      },
    })
  }

  return (
    <div className="space-y-4">
      <div className={`overflow-x-auto ${cardClass}`}>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className={thClass}>Site</th>
              <th className={thClass}>Send to</th>
              <th className={thClass}>Address</th>
              <th className={thClass}>Draft</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const site = siteOf(row.domain)
              const onSite = new Set(site.map((l) => l.recipient.id))
              const types = typesOf(recipientOf(row.recipientId))
              const drafts = row.recipientId
                ? draftsTo(row.recipientId, row.emailType)
                : []
              const target = drafts.find((d) => d.id === row.addTo)
              // links of this row the chosen draft already has
              const inTarget = target
                ? row.links.filter((l) =>
                    target.links.some((t) => t.id === l.id),
                  ).length
                : 0
              return (
                <tr
                  key={row.domain}
                  className={`border-b border-slate-100 last:border-0 ${
                    row.recipientId ? "" : "bg-amber-50/60"
                  }`}
                >
                  <td className={tdClass}>
                    <p className="font-medium text-slate-900">{row.domain}</p>
                    {!row.known && (
                      <span className="mt-1 inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                        <AlertTriangle className="size-3" />
                        Not in Config
                      </span>
                    )}
                    <div className="mt-1 space-y-0.5">
                      {row.links.map((l) => (
                        <p
                          key={l.id}
                          className="break-all text-xs text-slate-400"
                        >
                          {l.url}
                        </p>
                      ))}
                    </div>
                  </td>

                  <td className={`${tdClass} w-64`}>
                    <select
                      value={row.recipientId}
                      onChange={(e) => pickRecipient(row, e.target.value)}
                      aria-label={`Recipient for ${row.domain}`}
                      className={inputBase}
                    >
                      <option value="">Pick a recipient…</option>
                      {site.length > 0 && (
                        <optgroup label="On this site">
                          {site.map((l) => (
                            <option key={l.id} value={l.recipient.id}>
                              {l.recipient.name} ({RELATION_LABELS[l.relation]})
                            </option>
                          ))}
                        </optgroup>
                      )}
                      <optgroup label="Everyone">
                        {recipients
                          .filter((r) => !onSite.has(r.id))
                          .map((r) => (
                            <option key={r.id} value={r.id}>
                              {r.name}
                            </option>
                          ))}
                      </optgroup>
                    </select>
                    {row.recipientId && types.length === 0 && (
                      <p className="mt-1 text-xs text-amber-700">
                        No email address in Config. Add one before sending.
                      </p>
                    )}
                  </td>

                  <td className={`${tdClass} w-36`}>
                    {types.length > 0 && (
                      <select
                        value={row.emailType ?? ""}
                        onChange={(e) =>
                          update(row.domain, (r) => {
                            // a different address means a different draft
                            const emailType = e.target.value as EmailType
                            return {
                              ...r,
                              emailType,
                              addTo: defaultDraft(r.recipientId, emailType),
                            }
                          })
                        }
                        aria-label={`Address type for ${row.domain}`}
                        className={inputBase}
                      >
                        {types.map((t) => (
                          <option key={t} value={t}>
                            {EMAIL_TYPE_LABELS[t]}
                          </option>
                        ))}
                      </select>
                    )}
                  </td>

                  <td className={`${tdClass} w-56`}>
                    {drafts.length === 0 ? (
                      <span className="text-xs text-slate-500">
                        {row.recipientId ? "New email" : "–"}
                      </span>
                    ) : (
                      <>
                        <select
                          value={row.addTo}
                          onChange={(e) =>
                            update(row.domain, (r) => ({
                              ...r,
                              addTo: e.target.value,
                            }))
                          }
                          aria-label={`Draft for ${row.domain}`}
                          className={inputBase}
                        >
                          <option value="">New email</option>
                          {drafts.map((d) => (
                            <option key={d.id} value={d.id}>
                              {draftLabel(d)}
                            </option>
                          ))}
                        </select>
                        {inTarget > 0 && (
                          <p className="mt-1 text-xs text-slate-500">
                            {inTarget === row.links.length
                              ? "Already in this draft."
                              : `${inTarget} of ${row.links.length} links already in this draft, not added twice.`}
                          </p>
                        )}
                        {target?.is_body_custom && (
                          <p className="mt-1 text-xs text-amber-700">
                            This draft's body was edited by hand. Adding links
                            resets it to the template.
                          </p>
                        )}
                      </>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="text-sm text-slate-600">
        {ready.length === 0 ? (
          "Pick a recipient for at least one site."
        ) : (
          <>
            This will{" "}
            {[
              newEmails &&
                `create ${newEmails} new ${newEmails === 1 ? "draft" : "drafts"}`,
              addedTo &&
                `add to ${addedTo} existing ${addedTo === 1 ? "draft" : "drafts"}`,
            ]
              .filter(Boolean)
              .join(" and ")}
            .
          </>
        )}
        {skipped.length > 0 && (
          <p className="mt-1 text-xs text-amber-700">
            {skipped.map((r) => r.domain).join(", ")}: no recipient picked.
            These links stay on the case; use "Draft emails" later.
          </p>
        )}
      </div>

      <div className="flex justify-end gap-3">
        <button type="button" onClick={onCancel} className={btnSecondary}>
          Not now
        </button>
        <button
          type="button"
          disabled={ready.length === 0 || createDrafts.isPending}
          onClick={submit}
          className={btnPrimary}
        >
          {createDrafts.isPending ? "Creating…" : "Create drafts"}
        </button>
      </div>
    </div>
  )
}

/** The address types a recipient has, in the usual order. */
function typesOf(recipient: Recipient | undefined): EmailType[] {
  return TYPE_ORDER.filter((t) =>
    recipient?.emails.some((e) => e.email_type === t),
  )
}

/** "Add to draft: <address> · <first link> +N more", to tell drafts apart. */
function draftLabel(draft: TakedownEmail) {
  const [first, ...rest] = draft.links
  const link = first ? first.url.replace(/^https?:\/\//, "") : "no links"
  const more = rest.length ? ` +${rest.length} more` : ""
  return `Add to draft: ${draft.to_address ?? "no address"} · ${link}${more}`
}
