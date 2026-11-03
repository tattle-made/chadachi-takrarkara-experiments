import type {
  Attachment,
  AttachmentKind,
  CaseLink,
  Domain,
  LegalGround,
} from "./types"

// Mocked shared Gmail mailbox the emails are sent from.
export const SENDER_EMAIL = "takedowns@counsellors-org.example"

export function extractDomain(raw: string): string | null {
  const trimmed = raw.trim()
  if (!trimmed) return null
  try {
    const url = new URL(
      /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`,
    )
    const host = url.hostname.toLowerCase().replace(/^www\./, "")
    return host.includes(".") ? host : null
  } catch {
    return null
  }
}

export type ParsedLink = { url: string; domain: string | null }

// Splits pasted text into unique links. Invalid entries keep domain = null.
export function parseLinks(text: string): ParsedLink[] {
  const unique = [
    ...new Set(
      text
        .split(/[\s,]+/)
        .map((s) => s.trim())
        .filter(Boolean),
    ),
  ]
  return unique.map((url) => ({ url, domain: extractDomain(url) }))
}

export function suggestedRecipientId(
  domain: string,
  domains: Domain[],
): string | null {
  return domains.find((d) => d.domain === domain)?.recipientId ?? null
}

export function uniqueDomains(links: Pick<CaseLink, "domain">[]): string[] {
  return [...new Set(links.map((l) => l.domain))]
}

export function buildSubject(domains: string[]): string {
  const shown = domains.slice(0, 3).join(", ")
  const extra = domains.length > 3 ? ` +${domains.length - 3} more` : ""
  return `DMCA Takedown Request – ${shown}${extra}`
}

const ATTACHMENT_LABELS: Record<AttachmentKind, string> = {
  cyber_crime_report: "Cyber Crime Report",
  government_id: "Government issued ID card",
  other: "Other document",
}

export function attachmentLabel(attachment: Attachment): string {
  return attachment.kind === "other"
    ? attachment.fileName
    : ATTACHMENT_LABELS[attachment.kind]
}

export const ATTACHMENT_KIND_OPTIONS = Object.entries(ATTACHMENT_LABELS) as [
  AttachmentKind,
  string,
][]

type RenderInput = {
  fullName: string
  recipientName: string
  links: CaseLink[]
  legalGrounds: LegalGround[]
  attachments: Attachment[]
}

// Fills the counsellors' standard DMCA template.
export function renderBody({
  fullName,
  recipientName,
  links,
  legalGrounds,
  attachments,
}: RenderInput): string {
  const domains = uniqueDomains(links)

  const linksBlock =
    domains.length <= 1
      ? links.map((l) => l.url).join("\n")
      : domains
          .map((domain) => {
            const urls = links
              .filter((l) => l.domain === domain)
              .map((l) => `  ${l.url}`)
            return `${domain}:\n${urls.join("\n")}`
          })
          .join("\n")

  const groundsBlock =
    legalGrounds.length === 0
      ? `This incident unequivocally breaches ${recipientName}'s copyright infringement policy.`
      : `This incident unequivocally breaches ${recipientName}'s copyright infringement policy, along with the following:\n${legalGrounds
          .map((g) => `- ${g.citation}: ${g.clauseText}`)
          .join("\n")}`

  const attachmentsBlock =
    attachments.length > 0
      ? `Attachments:\n${attachments.map(attachmentLabel).join("\n")}`
      : null

  return [
    "Hi,",
    `This letter serves as official notification of copyright infringement pursuant to the Digital Millennium Copyright Act ("DMCA") 17 U.S.C. § 512(c)(3) for materials on ${domains.join(", ")}`,
    `${fullName} is the exclusive rights holder of the following copyrighted material that is posted without authorization on your website at the following link:\n${linksBlock}`,
    `The uploaded content is the possession of ${fullName} and the video has been uploaded without her consent.`,
    `Upon receipt of this notice, ${fullName} requests that you expeditiously remove or disable access to the materials identified above as being the subject of infringement.`,
    `${fullName} is providing this notice in good faith and with the reasonable belief that their rights as the exclusive rights holder are being infringed.`,
    `Under penalty of perjury, ${fullName} certifies that the information contained in this notification is both true and accurate and that they are the owner of the copyrighted material identified above.`,
    groundsBlock,
    "Furthermore, the unauthorized dissemination of non-consensual intimate material flagrantly violates Indian laws, including the Bharatiya Nayaya Sanhita 2023 and the Information Technology (IT) Act, 2000. These laws categorically prohibit and criminalize the publishing and transmission of such material, making this a punishable offense. A cybercrime report has been filed.",
    attachmentsBlock,
    "We implore you to take swift and decisive action to remove this content from your platform immediately. Failure to act promptly not only exacerbates the victim's trauma but also undermines your commitment to uphold the principles of the DMCA and relevant intellectual property laws.",
    "If you wish to discuss the matter further, please reply to this email.",
    "We appreciate your prompt attention to this matter.",
  ]
    .filter((block): block is string => block !== null)
    .join("\n\n")
}
