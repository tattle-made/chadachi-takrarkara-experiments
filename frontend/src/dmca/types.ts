// Shapes the DMCA API sends and accepts, named and spelled as in the backend
// (snake_case). ids are UUID strings, except users' ids (numbers). Dates are
// ISO strings.

// --- enums ---

export type EmailType = "dmca" | "abuse" | "csam" | "general"

export type DomainRelation = "website_owner" | "cdn" | "host" | "registrar"

// draft -> queued -> sending -> sent | failed
export type EmailStatus = "draft" | "queued" | "sending" | "sent" | "failed"

export type AttachmentKind =
  | "cyber_crime_report"
  | "government_id"
  | "age_proof"
  | "other"

export type GoogleConnectionStatus = "connected" | "broken"

// list endpoints wrap their rows like this
export type Page<T> = { data: T[]; count: number }

// --- users ---

export type UserSummary = { id: number; email: string }

// --- profiles and cases ---

export type ProfileSummary = {
  id: string
  full_name: string
  display_name: string | null
  created_at: string
}

export type ProfileInput = {
  full_name: string
  display_name?: string | null
  notes?: string | null
}

// a case as listed on its profile's page
export type ProfileCase = {
  id: string
  title: string
  is_minor: boolean
  created_at: string
  assignee: UserSummary | null
}

export type ProfileDetail = ProfileSummary & {
  notes: string | null
  cases: ProfileCase[]
}

export type CaseLink = {
  id: string
  url: string
  domain: string
  removed_at: string | null
  created_at: string
}

export type CaseSummary = ProfileCase & { profile: ProfileSummary }

export type CaseDetail = CaseSummary & { links: CaseLink[] }

export type CaseInput = {
  title: string
  is_minor?: boolean
  assigned_to?: number | null
}

// what happened to pasted links: new ones, ones the case had, and non-links
export type LinksAdded = {
  added: CaseLink[]
  skipped: string[]
  invalid: string[]
}

// --- documents ---

export type Attachment = {
  id: string
  profile_id: string
  kind: AttachmentKind
  file_name: string
  mime_type: string
  size: number // bytes
  created_at: string
}

// --- recipients (Config) ---

export type RecipientEmail = {
  id: string
  address: string
  email_type: EmailType
}

export type DomainLink = {
  id: string
  relation: DomainRelation
  domain: { id: string; domain: string }
}

export type Recipient = {
  id: string
  name: string
  notes: string | null
  created_at: string
  emails: RecipientEmail[]
  domain_links: DomainLink[]
}

export type RecipientInput = { name: string; notes?: string | null }

// GET /domains/resolve: who we email for each site
export type DomainResolved = {
  domain: string
  recipient_links: {
    id: string
    relation: DomainRelation
    recipient: { id: string; name: string; email_types: EmailType[] }
  }[]
}

// --- legal grounds (Config) ---

export type LegalGround = {
  id: string
  title: string
  citation: string
  clause_text: string
  default_selected: boolean
  minor_only: boolean
  active: boolean
  created_at: string
}

export type LegalGroundInput = Omit<LegalGround, "id" | "created_at">

// --- emails ---

export type TakedownEmail = {
  id: string
  case_id: string
  recipient_id: string | null
  recipient_name: string
  relation: DomainRelation | null
  email_type: EmailType | null
  to_address: string | null
  subject: string
  // what will be (or was) sent
  body: string
  // true once the counsellor edited the body by hand
  is_body_custom: boolean
  links: CaseLink[]
  legal_grounds: LegalGround[]
  attachments: Attachment[]
  status: EmailStatus
  attempts: number
  last_error: string | null
  // failed, or stuck in "sending": show a Retry button
  can_retry: boolean
  sent_at: string | null
  reply_received_at: string | null
  // sent over 48 hours ago with no reply marked: "No reply · 48h+"
  no_reply_48h: boolean
  created_at: string
}

export type EmailFilters = {
  case_id?: string
  status?: EmailStatus
  no_reply_48h?: boolean
}

// one review-screen row: a site and who to email about it
export type DraftItem = {
  domain: string
  recipient_id: string
  email_type?: EmailType | null
  relation?: DomainRelation | null
  // put this site's links into an existing draft instead of a new one
  add_to_email_id?: string | null
}

export type DraftsResult = {
  created: TakedownEmail[]
  updated: TakedownEmail[]
}

// leave a field out to keep it; custom_body: null goes back to the template
export type EmailUpdate = {
  to_address?: string | null
  subject?: string
  custom_body?: string | null
  link_ids?: string[]
  legal_ground_ids?: string[]
  attachment_ids?: string[]
}

// GET /emails/{id}/escalation: who to email next about each site
// (recipient_id is null when there's nobody further up the chain)
export type EscalationSuggestion = {
  domain: string
  recipient_id: string | null
  recipient_name: string | null
  relation: DomainRelation | null
}

// --- Google connection ---

export type GoogleStatus = {
  connected: boolean
  status: GoogleConnectionStatus | null
  account_email: string | null
  connected_at: string | null
  last_error: string | null
}
