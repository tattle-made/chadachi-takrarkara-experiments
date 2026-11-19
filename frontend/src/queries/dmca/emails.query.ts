// Takedown emails: drafts, editing, sending, and what happens after sending.
import {
  queryOptions,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query"
import { toastError } from "@/dmca/errors"
import type {
  DraftItem,
  DraftsResult,
  EmailFilters,
  EmailUpdate,
  EscalationSuggestion,
  TakedownEmail,
} from "@/dmca/types"
import apiClient from "@/lib/apiClient"

const API = "/api/v1/dmca"
const EMAILS = ["dmca", "emails"] as const

// while the queue is working on an email, check again this often
const POLL_MS = 3000

const isInQueue = (email: TakedownEmail) =>
  email.status === "queued" || email.status === "sending"

/** Emails, newest first. Keeps refreshing while any of them is being sent, so
 * "sent" / "failed" show up without reloading. */
export const emailsQueryOptions = (filters: EmailFilters = {}) =>
  queryOptions({
    queryKey: [...EMAILS, filters],
    queryFn: async () => {
      const response = await apiClient.get<TakedownEmail[]>(`${API}/emails`, {
        params: filters,
      })
      return response.data
    },
    refetchInterval: (query) =>
      query.state.data?.some(isInQueue) ? POLL_MS : false,
  })

/** Who to email next about each site in a sent email (for Escalate). */
export const escalationQueryOptions = (emailId: string) =>
  queryOptions({
    queryKey: ["dmca", "escalation", emailId],
    queryFn: async () => {
      const response = await apiClient.get<EscalationSuggestion[]>(
        `${API}/emails/${emailId}/escalation`,
      )
      return response.data
    },
    staleTime: 0,
  })

/** Create drafts from the review screen's rows (also used by Escalate). */
export const useCreateDrafts = (caseId: string) => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (items: DraftItem[]) => {
      const response = await apiClient.post<DraftsResult>(
        `${API}/cases/${caseId}/drafts`,
        { items },
      )
      return response.data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: EMAILS }),
    onError: toastError,
  })
}

/** Edit a draft. Send only the fields that changed (see EmailUpdate). */
export const useUpdateEmail = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, ...changes }: EmailUpdate & { id: string }) => {
      const response = await apiClient.patch<TakedownEmail>(
        `${API}/emails/${id}`,
        changes,
      )
      return response.data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: EMAILS }),
    onError: toastError,
  })
}

/** Delete a draft. Drafts only: the backend refuses others with a 409. */
export const useDeleteEmail = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (emailId: string) => {
      await apiClient.delete(`${API}/emails/${emailId}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: EMAILS }),
    onError: toastError,
  })
}

/** Hand drafts to the background queue. All or nothing. */
export const useSendEmails = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (emailIds: string[]) => {
      const response = await apiClient.post<TakedownEmail[]>(
        `${API}/emails/send`,
        { email_ids: emailIds },
      )
      return response.data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: EMAILS }),
    onError: toastError,
  })
}

/** Send a failed (or stuck) email again. */
export const useRetryEmail = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (emailId: string) => {
      const response = await apiClient.post<TakedownEmail>(
        `${API}/emails/${emailId}/retry`,
      )
      return response.data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: EMAILS }),
    onError: toastError,
  })
}

/** Mark or unmark "Got a reply" on a sent email. */
export const useSetReplyReceived = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, received }: { id: string; received: boolean }) => {
      const response = await apiClient.put<TakedownEmail>(
        `${API}/emails/${id}/reply-received`,
        { received },
      )
      return response.data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: EMAILS }),
    onError: toastError,
  })
}
