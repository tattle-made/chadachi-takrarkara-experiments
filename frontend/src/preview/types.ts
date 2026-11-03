// Draft schema for the DMCA takedown flow.
// The UI preview uses these types for its dummy data and forms; they are meant
// to map closely to DB tables once the backend is built.

export type Profile = {
  id: string
  fullName: string
  notes?: string
  createdAt: string
}

export type Case = {
  id: string
  profileId: string
  title: string
  createdAt: string
}

export type AttachmentKind = "cyber_crime_report" | "government_id" | "other"

// Documents live on the person's profile and can be attached to any of
// emails; each email picks its own (none by default).
// Add-only: never deleted, so sent emails keep a complete trail.
// Preview: files are kept in memory only (`file`), seeded rows have none.
export type Attachment = {
  id: string
  profileId: string
  kind: AttachmentKind
  fileName: string
  sizeKb: number
  uploadedAt: string
  file?: File
}

export type CaseLink = {
  id: string
  caseId: string
  url: string
  domain: string
}

export type RecipientKind = "platform" | "service_provider"

// Who we email. Admin-managed.
export type Recipient = {
  id: string
  name: string
  kind: RecipientKind
  emails: string[]
}

// A known domain and the recipient it's suggested for. Counsellors can still
// pick any recipient per case; this only pre-fills the choice.
export type Domain = {
  domain: string
  recipientId: string
}

// Standard clauses cited in the email, picked per draft with checkboxes.
export type LegalGround = {
  id: string
  title: string
  citation: string
  clauseText: string
  defaultSelected: boolean
  active: boolean
}

export type EmailStatus = "draft" | "queued" | "sending" | "sent" | "failed"

export type TakedownEmail = {
  id: string
  caseId: string
  recipientId: string
  linkIds: string[]
  legalGroundIds: string[]
  attachmentIds: string[]
  subject: string
  // null = generated from the template; a string = edited by the counsellor
  customBody: string | null
  status: EmailStatus
  attempts: number
  lastError?: string
  gmailMessageId?: string
  sentAt?: string
  createdAt: string
}
