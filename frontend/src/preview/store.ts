import { create } from "zustand"
import * as seed from "./data"
import { buildSubject, uniqueDomains } from "./template"
import type {
  Attachment,
  AttachmentKind,
  Case,
  CaseLink,
  Domain,
  LegalGround,
  Profile,
  Recipient,
  RecipientKind,
  TakedownEmail,
} from "./types"

type PreviewData = {
  profiles: Profile[]
  cases: Case[]
  attachments: Attachment[]
  links: CaseLink[]
  recipients: Recipient[]
  domains: Domain[]
  legalGrounds: LegalGround[]
  emails: TakedownEmail[]
}

export type DraftGroup = {
  recipientId: string
  links: { url: string; domain: string }[]
}

type EmailPatch = Partial<
  Pick<
    TakedownEmail,
    | "subject"
    | "customBody"
    | "legalGroundIds"
    | "attachmentIds"
    | "recipientId"
  >
>

type PreviewStore = PreviewData & {
  addProfile: (input: { fullName: string; notes?: string }) => string
  addCase: (input: { profileId: string; title: string }) => string
  addAttachments: (profileId: string, files: NewFile[]) => void
  addLinksAndDrafts: (caseId: string, groups: DraftGroup[]) => void
  updateEmail: (id: string, patch: EmailPatch) => void
  sendEmails: (ids: string[]) => void
  retryEmail: (id: string) => void
  addRecipient: (input: {
    name: string
    kind: RecipientKind
    email: string
  }) => string
  addDomain: (domain: string, recipientId: string) => void
  removeDomain: (domain: string) => void
  addLegalGround: (input: Omit<LegalGround, "id">) => void
  updateLegalGround: (id: string, patch: Partial<LegalGround>) => void
  resetDemo: () => void
}

const uid = (prefix: string) =>
  `${prefix}_${Math.random().toString(36).slice(2, 9)}`
const now = () => new Date().toISOString()

const initialData = (): PreviewData => ({
  profiles: [...seed.profiles],
  cases: [...seed.cases],
  attachments: [...seed.attachments],
  links: [...seed.links],
  recipients: [...seed.recipients],
  domains: [...seed.domains],
  legalGrounds: [...seed.legalGrounds],
  emails: [...seed.emails],
})

type NewFile = { kind: AttachmentKind; file: File }

function toAttachments(profileId: string, files: NewFile[]): Attachment[] {
  return files.map(({ kind, file }) => ({
    id: uid("a"),
    profileId,
    kind,
    fileName: file.name,
    sizeKb: Math.max(1, Math.round(file.size / 1024)),
    uploadedAt: now(),
    file,
  }))
}

// ── Simulated send queue ───────────────────────────────────────────────
// Stands in for the Postgres queue + worker: one email at a time, with
// automatic retries before an email is marked failed.

const STEP_MS = 900
const MAX_ATTEMPTS = 3
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))
let queue: Promise<void> = Promise.resolve()

function enqueue(id: string, manualRetry: boolean) {
  queue = queue.then(() => processEmail(id, manualRetry))
}

async function processEmail(id: string, manualRetry: boolean) {
  const current = () =>
    usePreviewStore.getState().emails.find((e) => e.id === id)
  const patch = (p: Partial<TakedownEmail>) =>
    usePreviewStore.setState((s) => ({
      emails: s.emails.map((e) => (e.id === id ? { ...e, ...p } : e)),
    }))

  const email = current()
  if (!email || email.status !== "queued") return
  const willFail =
    !manualRetry &&
    seed.SIMULATED_FAILURE_RECIPIENT_IDS.includes(email.recipientId)

  await sleep(STEP_MS / 2)
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    patch({ status: "sending", attempts: (current()?.attempts ?? 0) + 1 })
    await sleep(STEP_MS)
    if (!willFail) {
      patch({
        status: "sent",
        sentAt: now(),
        gmailMessageId: Math.random().toString(16).slice(2, 18),
        lastError: undefined,
      })
      return
    }
  }
  patch({
    status: "failed",
    lastError: "Gmail API 503: backend error (simulated)",
  })
}

// ── Store ──────────────────────────────────────────────────────────────

export const usePreviewStore = create<PreviewStore>()((set, get) => ({
  ...initialData(),

  addProfile: ({ fullName, notes }) => {
    const id = uid("p")
    set((s) => ({
      profiles: [
        { id, fullName, notes: notes || undefined, createdAt: now() },
        ...s.profiles,
      ],
    }))
    return id
  },

  addCase: ({ profileId, title }) => {
    const id = uid("c")
    set((s) => ({
      cases: [...s.cases, { id, profileId, title, createdAt: now() }],
    }))
    return id
  },

  // Not ticked on any email: counsellors choose attachments per email.
  addAttachments: (profileId, files) => {
    set((s) => ({
      attachments: [...s.attachments, ...toAttachments(profileId, files)],
    }))
  },

  addLinksAndDrafts: (caseId, groups) => {
    set((s) => {
      const existingUrls = new Set(
        s.links.filter((l) => l.caseId === caseId).map((l) => l.url),
      )
      const defaultGroundIds = s.legalGrounds
        .filter((g) => g.active && g.defaultSelected)
        .map((g) => g.id)

      const allLinks = [...s.links]
      let emails = [...s.emails]

      for (const group of groups) {
        const created: CaseLink[] = group.links
          .filter((l) => !existingUrls.has(l.url))
          .map((l) => ({ id: uid("l"), caseId, url: l.url, domain: l.domain }))
        if (created.length === 0) continue
        allLinks.push(...created)

        // New links join this case's open draft for the same recipient.
        const openDraft = emails.find(
          (e) =>
            e.caseId === caseId &&
            e.recipientId === group.recipientId &&
            e.status === "draft",
        )
        if (openDraft) {
          const linkIds = [...openDraft.linkIds, ...created.map((l) => l.id)]
          const draftLinks = allLinks.filter((l) => linkIds.includes(l.id))
          emails = emails.map((e) =>
            e.id === openDraft.id
              ? {
                  ...e,
                  linkIds,
                  subject: buildSubject(uniqueDomains(draftLinks)),
                }
              : e,
          )
        } else {
          emails.push({
            id: uid("e"),
            caseId,
            recipientId: group.recipientId,
            linkIds: created.map((l) => l.id),
            legalGroundIds: defaultGroundIds,
            attachmentIds: [],
            subject: buildSubject(uniqueDomains(created)),
            customBody: null,
            status: "draft",
            attempts: 0,
            createdAt: now(),
          })
        }
      }

      return { links: allLinks, emails }
    })
  },

  updateEmail: (id, patch) => {
    set((s) => ({
      emails: s.emails.map((e) =>
        e.id === id && e.status === "draft" ? { ...e, ...patch } : e,
      ),
    }))
  },

  sendEmails: (ids) => {
    const sendable = get()
      .emails.filter((e) => ids.includes(e.id) && e.status === "draft")
      .map((e) => e.id)
    set((s) => ({
      emails: s.emails.map((e) =>
        sendable.includes(e.id) ? { ...e, status: "queued" } : e,
      ),
    }))
    for (const id of sendable) enqueue(id, false)
  },

  retryEmail: (id) => {
    if (get().emails.find((e) => e.id === id)?.status !== "failed") return
    set((s) => ({
      emails: s.emails.map((e) =>
        e.id === id ? { ...e, status: "queued", lastError: undefined } : e,
      ),
    }))
    enqueue(id, true)
  },

  addRecipient: ({ name, kind, email }) => {
    const id = uid("r")
    set((s) => ({
      recipients: [...s.recipients, { id, name, kind, emails: [email] }],
    }))
    return id
  },

  // One recipient per domain: adding a domain that's already known moves it.
  addDomain: (domain, recipientId) => {
    set((s) => ({
      domains: [
        ...s.domains.filter((d) => d.domain !== domain),
        { domain, recipientId },
      ],
    }))
  },

  removeDomain: (domain) => {
    set((s) => ({ domains: s.domains.filter((d) => d.domain !== domain) }))
  },

  addLegalGround: (input) => {
    set((s) => ({
      legalGrounds: [...s.legalGrounds, { ...input, id: uid("lg") }],
    }))
  },

  updateLegalGround: (id, patch) => {
    set((s) => ({
      legalGrounds: s.legalGrounds.map((g) =>
        g.id === id ? { ...g, ...patch } : g,
      ),
    }))
  },

  resetDemo: () => set(initialData()),
}))
