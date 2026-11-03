import type { usePreviewStore } from "./store"
import { renderBody } from "./template"
import type { TakedownEmail } from "./types"

type State = ReturnType<typeof usePreviewStore.getState>

// Resolves everything an email row/card needs, including the rendered body.
export function emailView(state: State, email: TakedownEmail) {
  const caseItem = state.cases.find((c) => c.id === email.caseId)
  const profile = state.profiles.find((p) => p.id === caseItem?.profileId)
  const recipient = state.recipients.find((r) => r.id === email.recipientId)
  const links = state.links.filter((l) => email.linkIds.includes(l.id))
  const grounds = state.legalGrounds.filter((g) =>
    email.legalGroundIds.includes(g.id),
  )
  const available = state.attachments.filter((a) => a.profileId === profile?.id)
  const attachments = available.filter((a) =>
    email.attachmentIds.includes(a.id),
  )
  const generatedBody = renderBody({
    fullName: profile?.fullName ?? "",
    recipientName: recipient?.name ?? "",
    links,
    legalGrounds: grounds,
    attachments,
  })

  return {
    caseItem,
    profile,
    recipient,
    links,
    grounds,
    available,
    attachments,
    generatedBody,
    body: email.customBody ?? generatedBody,
  }
}
