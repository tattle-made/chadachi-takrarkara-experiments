// How the API's codes are shown in the UI.
import type {
  AttachmentKind,
  DomainRelation,
  EmailStatus,
  EmailType,
  ProfileSummary,
} from "./types"

export const ATTACHMENT_KIND_LABELS: Record<AttachmentKind, string> = {
  cyber_crime_report: "Cyber crime report",
  government_id: "Government ID",
  age_proof: "Age proof",
  other: "Other document",
}

export const RELATION_LABELS: Record<DomainRelation, string> = {
  website_owner: "Website owner",
  cdn: "CDN",
  host: "Host",
  registrar: "Registrar",
}

export const EMAIL_TYPE_LABELS: Record<EmailType, string> = {
  dmca: "DMCA",
  abuse: "Abuse",
  csam: "CSAM",
  general: "General",
}

export const STATUS_LABELS: Record<EmailStatus, string> = {
  draft: "Draft",
  queued: "Queued",
  sending: "Sending",
  sent: "Sent",
  failed: "Failed",
}

/** The name to show in lists: the internal label if set, else the full name. */
export const profileName = (profile: ProfileSummary) =>
  profile.display_name || profile.full_name

/** A file size for people, e.g. "1.4 MB" or "320 KB". */
export const formatSize = (bytes: number) =>
  bytes >= 1024 * 1024
    ? `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`
