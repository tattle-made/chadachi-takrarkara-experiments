// Config: recipients (with their addresses and sites), legal grounds, and the
// Google connection. Reads are open to everyone; changes are admin only.
import {
  queryOptions,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query"
import { toastError } from "@/dmca/errors"
import type {
  DomainRelation,
  DomainResolved,
  EmailType,
  GoogleStatus,
  LegalGround,
  LegalGroundInput,
  Page,
  Recipient,
  RecipientInput,
} from "@/dmca/types"
import apiClient from "@/lib/apiClient"

const API = "/api/v1/dmca"
// recipient changes also change who a site resolves to
const RECIPIENTS = ["dmca", "recipients"] as const
const RESOLVE = ["dmca", "resolve"] as const
const LEGAL_GROUNDS = ["dmca", "legal-grounds"] as const
const GOOGLE = ["dmca", "google"] as const

// --- recipients ---

/** All recipients, with their addresses and sites. */
export const recipientsQueryOptions = () =>
  queryOptions({
    queryKey: RECIPIENTS,
    queryFn: async () => {
      const response = await apiClient.get<Page<Recipient>>(
        `${API}/recipients`,
        { params: { limit: 1000 } },
      )
      return response.data
    },
  })

/** Who we email for each of these sites, to pre-fill the review screen. */
export const resolveDomainsQueryOptions = (domains: string[]) =>
  queryOptions({
    queryKey: [...RESOLVE, [...domains].sort()],
    queryFn: async () => {
      const response = await apiClient.get<DomainResolved[]>(
        `${API}/domains/resolve`,
        { params: { domains: domains.join(",") } },
      )
      return response.data
    },
    enabled: domains.length > 0,
  })

/** Wraps a recipient-changing request: refresh recipients and site lookups
 * after it, and toast its error. */
const useRecipientMutation = <T>(request: (input: T) => Promise<unknown>) => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: request,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: RECIPIENTS })
      queryClient.invalidateQueries({ queryKey: RESOLVE })
    },
    onError: toastError,
  })
}

/** Add a recipient. */
export const useCreateRecipient = () =>
  useRecipientMutation((input: RecipientInput) =>
    apiClient.post<Recipient>(`${API}/recipients`, input),
  )

/** Edit a recipient's name or notes. */
export const useUpdateRecipient = () =>
  useRecipientMutation(
    ({ id, ...input }: Partial<RecipientInput> & { id: string }) =>
      apiClient.patch(`${API}/recipients/${id}`, input),
  )

/** Delete a recipient. */
export const useDeleteRecipient = () =>
  useRecipientMutation((id: string) =>
    apiClient.delete(`${API}/recipients/${id}`),
  )

/** Add an address (with its type, e.g. abuse) to a recipient. */
export const useAddRecipientEmail = () =>
  useRecipientMutation(
    ({
      recipientId,
      ...input
    }: {
      recipientId: string
      address: string
      email_type: EmailType
    }) => apiClient.post(`${API}/recipients/${recipientId}/emails`, input),
  )

/** Remove an address from a recipient. */
export const useDeleteRecipientEmail = () =>
  useRecipientMutation(
    ({ recipientId, emailId }: { recipientId: string; emailId: string }) =>
      apiClient.delete(`${API}/recipients/${recipientId}/emails/${emailId}`),
  )

/** Link a site to a recipient with its role (e.g. cdn). */
export const useAddRecipientDomain = () =>
  useRecipientMutation(
    ({
      recipientId,
      ...input
    }: {
      recipientId: string
      domain: string
      relation: DomainRelation
    }) => apiClient.post(`${API}/recipients/${recipientId}/domains`, input),
  )

/** Unlink a site from a recipient. */
export const useDeleteRecipientDomain = () =>
  useRecipientMutation(
    ({ recipientId, linkId }: { recipientId: string; linkId: string }) =>
      apiClient.delete(`${API}/recipients/${recipientId}/domains/${linkId}`),
  )

// --- legal grounds ---

/** Active grounds only, unless includeInactive (Config shows all). */
export const legalGroundsQueryOptions = (includeInactive = false) =>
  queryOptions({
    queryKey: [...LEGAL_GROUNDS, includeInactive],
    queryFn: async () => {
      const response = await apiClient.get<Page<LegalGround>>(
        `${API}/legal-grounds`,
        { params: { include_inactive: includeInactive } },
      )
      return response.data
    },
  })

/** Wraps a legal-ground-changing request: refresh the lists and toast errors. */
const useLegalGroundMutation = <T>(request: (input: T) => Promise<unknown>) => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: request,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: LEGAL_GROUNDS }),
    onError: toastError,
  })
}

/** Add a legal ground. */
export const useCreateLegalGround = () =>
  useLegalGroundMutation((input: LegalGroundInput) =>
    apiClient.post(`${API}/legal-grounds`, input),
  )

/** Edit a legal ground (including turning it on or off). */
export const useUpdateLegalGround = () =>
  useLegalGroundMutation(
    ({ id, ...input }: Partial<LegalGroundInput> & { id: string }) =>
      apiClient.patch(`${API}/legal-grounds/${id}`, input),
  )

/** Delete a legal ground. Refused (409) once any email has used it. */
export const useDeleteLegalGround = () =>
  useLegalGroundMutation((id: string) =>
    apiClient.delete(`${API}/legal-grounds/${id}`),
  )

// --- Google connection ---

/** Whether Google is connected, and with which account. */
export const googleStatusQueryOptions = () =>
  queryOptions({
    queryKey: GOOGLE,
    queryFn: async () => {
      const response = await apiClient.get<GoogleStatus>(
        "/api/v1/google/status",
      )
      return response.data
    },
  })

/** Send the browser to Google's sign-in. Google sends it back to
 * /dmca/config?google=connected (or =error&reason=...). */
export const useConnectGoogle = () =>
  useMutation({
    mutationFn: async () => {
      const response = await apiClient.get<{ url: string }>(
        "/api/v1/google/connect",
      )
      window.location.assign(response.data.url)
    },
    onError: toastError,
  })

/** Forget the stored Google token. */
export const useDisconnectGoogle = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      await apiClient.delete("/api/v1/google")
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: GOOGLE }),
    onError: toastError,
  })
}
