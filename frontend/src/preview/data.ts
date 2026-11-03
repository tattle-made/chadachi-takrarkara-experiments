// Dummy data for the UI preview. Everything here is fictional.
import { buildSubject } from "./template"
import type {
  Attachment,
  Case,
  CaseLink,
  Domain,
  LegalGround,
  Profile,
  Recipient,
  TakedownEmail,
} from "./types"

export const profiles: Profile[] = [
  {
    id: "p_jane_doe",
    fullName: "Jane Doe",
    notes: "Prefers contact over WhatsApp.",
    createdAt: "2026-09-12T10:00:00Z",
  },
  {
    id: "p_jane_roe",
    fullName: "Jane Roe",
    createdAt: "2026-10-02T08:30:00Z",
  },
  {
    id: "p_mary_major",
    fullName: "Mary Major",
    notes: "Referred by partner NGO.",
    createdAt: "2026-10-20T14:15:00Z",
  },
]

export const cases: Case[] = [
  {
    id: "c_jane_doe_1",
    profileId: "p_jane_doe",
    title: "Video leak – Sept 2026",
    createdAt: "2026-09-12T10:20:00Z",
  },
  {
    id: "c_jane_roe_1",
    profileId: "p_jane_roe",
    title: "Photos reposted on image sites",
    createdAt: "2026-10-02T09:00:00Z",
  },
]

export const attachments: Attachment[] = [
  {
    id: "a_1",
    profileId: "p_jane_doe",
    kind: "cyber_crime_report",
    fileName: "cybercrime-complaint.pdf",
    sizeKb: 412,
    uploadedAt: "2026-09-12T10:20:00Z",
  },
  {
    id: "a_2",
    profileId: "p_jane_doe",
    kind: "government_id",
    fileName: "govt-id.pdf",
    sizeKb: 230,
    uploadedAt: "2026-09-12T10:05:00Z",
  },
  {
    id: "a_3",
    profileId: "p_jane_roe",
    kind: "cyber_crime_report",
    fileName: "ncrp-acknowledgement.pdf",
    sizeKb: 198,
    uploadedAt: "2026-10-02T09:00:00Z",
  },
]

export const recipients: Recipient[] = [
  {
    id: "r_clipvault",
    name: "ClipVault",
    kind: "platform",
    emails: ["legal@clipvault.example"],
  },
  {
    id: "r_streamhub",
    name: "StreamHub",
    kind: "platform",
    emails: ["dmca@streamhub.example"],
  },
  {
    id: "r_picshare",
    name: "PicShare",
    kind: "platform",
    emails: ["copyright@picshare.example"],
  },
  {
    id: "r_talkboard",
    name: "TalkBoard",
    kind: "platform",
    emails: ["moderation@talkboard.example"],
  },
  {
    id: "r_cloudflare",
    name: "Cloudflare",
    kind: "service_provider",
    emails: ["abuse@cloudflare.example"],
  },
  {
    id: "r_hostnest",
    name: "HostNest",
    kind: "service_provider",
    emails: ["abuse@hostnest.example"],
  },
]

export const domains: Domain[] = [
  // ClipVault and its mirrors
  { domain: "clipvault.example", recipientId: "r_clipvault" },
  { domain: "clipvault-mirror.example", recipientId: "r_clipvault" },
  { domain: "cv-videos.example", recipientId: "r_clipvault" },
  { domain: "streamhub.example", recipientId: "r_streamhub" },
  { domain: "picshare.example", recipientId: "r_picshare" },
  { domain: "talkboard.example", recipientId: "r_talkboard" },
  // Sites with no policy of their own
  { domain: "shadytube.example", recipientId: "r_cloudflare" },
  { domain: "leakzone.example", recipientId: "r_cloudflare" },
  { domain: "fastclips.example", recipientId: "r_cloudflare" },
  { domain: "xvidz-free.example", recipientId: "r_hostnest" },
]

// Placeholder clause text, to be replaced with wording from the counsellors.
export const legalGrounds: LegalGround[] = [
  {
    id: "lg_dmca",
    title: "DMCA takedown notice",
    citation: "17 U.S.C. § 512(c)(3)",
    clauseText:
      "A service provider that receives a valid notice of infringement must act expeditiously to remove or disable access to the infringing material.",
    defaultSelected: true,
    active: true,
  },
  {
    id: "lg_it_rules",
    title: "24-hour removal of intimate imagery",
    citation: "IT Rules 2021, Rule 3(2)(b)",
    clauseText:
      "Intermediaries must remove, within 24 hours of a complaint, content that exposes an individual's private area, shows them in full or partial nudity or a sexual act, or impersonates them, including morphed images.",
    defaultSelected: true,
    active: true,
  },
  {
    id: "lg_it_act",
    title: "Privacy violation and obscene material",
    citation: "IT Act 2000, §§ 66E, 67, 67A",
    clauseText:
      "Capturing or transmitting images of a person's private areas without consent, and publishing or transmitting obscene or sexually explicit material electronically, are punishable offences.",
    defaultSelected: true,
    active: true,
  },
  {
    id: "lg_bns",
    title: "Voyeurism",
    citation: "Bharatiya Nyaya Sanhita 2023, § 77",
    clauseText:
      "Disseminating images of a woman engaged in a private act without her consent is a punishable offence, even where she consented to the recording.",
    defaultSelected: true,
    active: true,
  },
]

export const links: CaseLink[] = [
  {
    id: "l_1",
    caseId: "c_jane_doe_1",
    url: "https://clipvault.example/v/8812",
    domain: "clipvault.example",
  },
  {
    id: "l_2",
    caseId: "c_jane_doe_1",
    url: "https://clipvault-mirror.example/v/8812",
    domain: "clipvault-mirror.example",
  },
  {
    id: "l_3",
    caseId: "c_jane_doe_1",
    url: "https://shadytube.example/watch?v=a1b2c3",
    domain: "shadytube.example",
  },
  {
    id: "l_4",
    caseId: "c_jane_doe_1",
    url: "https://leakzone.example/p/77",
    domain: "leakzone.example",
  },
  {
    id: "l_5",
    caseId: "c_jane_roe_1",
    url: "https://picshare.example/i/5521",
    domain: "picshare.example",
  },
  {
    id: "l_6",
    caseId: "c_jane_roe_1",
    url: "https://xvidz-free.example/v/93",
    domain: "xvidz-free.example",
  },
]

const ALL_GROUNDS = legalGrounds.map((g) => g.id)

export const emails: TakedownEmail[] = [
  {
    id: "e_1",
    caseId: "c_jane_doe_1",
    recipientId: "r_clipvault",
    linkIds: ["l_1", "l_2"],
    legalGroundIds: ALL_GROUNDS,
    attachmentIds: ["a_1", "a_2"],
    subject: buildSubject(["clipvault.example", "clipvault-mirror.example"]),
    customBody: null,
    status: "sent",
    attempts: 1,
    gmailMessageId: "18f2c0a9d1e7b4aa",
    sentAt: "2026-09-12T11:02:00Z",
    createdAt: "2026-09-12T10:40:00Z",
  },
  {
    id: "e_2",
    caseId: "c_jane_doe_1",
    recipientId: "r_cloudflare",
    linkIds: ["l_3", "l_4"],
    legalGroundIds: ALL_GROUNDS,
    attachmentIds: [],
    subject: buildSubject(["shadytube.example", "leakzone.example"]),
    customBody: null,
    status: "draft",
    attempts: 0,
    createdAt: "2026-09-12T10:40:00Z",
  },
  {
    id: "e_3",
    caseId: "c_jane_roe_1",
    recipientId: "r_picshare",
    linkIds: ["l_5"],
    legalGroundIds: ALL_GROUNDS,
    attachmentIds: [],
    subject: buildSubject(["picshare.example"]),
    customBody: null,
    status: "draft",
    attempts: 0,
    createdAt: "2026-10-02T09:10:00Z",
  },
  {
    id: "e_4",
    caseId: "c_jane_roe_1",
    recipientId: "r_hostnest",
    linkIds: ["l_6"],
    legalGroundIds: ALL_GROUNDS,
    attachmentIds: ["a_3"],
    subject: buildSubject(["xvidz-free.example"]),
    customBody: null,
    status: "failed",
    attempts: 3,
    lastError: "Gmail API 503: backend error (simulated)",
    createdAt: "2026-10-02T09:10:00Z",
  },
]

// Preview only: emails to these recipients fail every queued attempt, so the
// recording can show the "failed → Retry" path. A manual retry succeeds.
export const SIMULATED_FAILURE_RECIPIENT_IDS = ["r_hostnest"]

// Handy for the recording: a mix of mirrors, Cloudflare-backed and unknown sites.
export const SAMPLE_LINKS = [
  "https://clipvault.example/v/9001",
  "https://cv-videos.example/watch/9001",
  "https://streamhub.example/video/55af",
  "https://fastclips.example/c/2231",
  "https://leakzone.example/p/912",
  "https://new-site.example/post/8",
].join("\n")
