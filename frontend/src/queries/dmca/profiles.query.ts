// Profiles, their cases, and each case's links.
import {
  queryOptions,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query"
import { toastError } from "@/dmca/errors"
import type {
  CaseDetail,
  CaseInput,
  CaseSummary,
  LinksAdded,
  Page,
  ProfileDetail,
  ProfileInput,
  ProfileSummary,
  UserSummary,
} from "@/dmca/types"
import apiClient from "@/lib/apiClient"

const API = "/api/v1/dmca"
// a profile's page lists its cases, so case changes refresh both
const PROFILES = ["dmca", "profiles"] as const
const CASES = ["dmca", "cases"] as const

/** Profiles list, optionally searched by name. */
export const profilesQueryOptions = (q = "") =>
  queryOptions({
    queryKey: [...PROFILES, "list", q],
    queryFn: async () => {
      const response = await apiClient.get<Page<ProfileSummary>>(
        `${API}/profiles`,
        { params: q ? { q } : {} },
      )
      return response.data
    },
  })

/** One profile, with its cases. */
export const profileQueryOptions = (profileId: string) =>
  queryOptions({
    queryKey: [...PROFILES, profileId],
    queryFn: async () => {
      const response = await apiClient.get<ProfileDetail>(
        `${API}/profiles/${profileId}`,
      )
      return response.data
    },
  })

/** One case, with its links. */
export const caseQueryOptions = (caseId: string) =>
  queryOptions({
    queryKey: [...CASES, caseId],
    queryFn: async () => {
      const response = await apiClient.get<CaseDetail>(`${API}/cases/${caseId}`)
      return response.data
    },
  })

/** All cases (newest first), e.g. to name each email's case in the outbox. */
export const casesQueryOptions = () =>
  queryOptions({
    queryKey: [...CASES, "list"],
    queryFn: async () => {
      const response = await apiClient.get<Page<CaseSummary>>(`${API}/cases`, {
        params: { limit: 1000 },
      })
      return response.data
    },
  })

/** Users a case can be assigned to. */
export const assigneesQueryOptions = () =>
  queryOptions({
    queryKey: ["dmca", "assignees"],
    queryFn: async () => {
      const response = await apiClient.get<UserSummary[]>(`${API}/assignees`)
      return response.data
    },
    staleTime: 5 * 60_000,
  })

/** Create a profile. */
export const useCreateProfile = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: ProfileInput) => {
      const response = await apiClient.post<ProfileDetail>(
        `${API}/profiles`,
        input,
      )
      return response.data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PROFILES }),
    onError: toastError,
  })
}

/** Edit a profile's name or notes. */
export const useUpdateProfile = (profileId: string) => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: Partial<ProfileInput>) => {
      const response = await apiClient.patch<ProfileDetail>(
        `${API}/profiles/${profileId}`,
        input,
      )
      return response.data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PROFILES }),
    onError: toastError,
  })
}

/** Create a case under a profile. */
export const useCreateCase = (profileId: string) => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: CaseInput) => {
      const response = await apiClient.post<CaseDetail>(
        `${API}/profiles/${profileId}/cases`,
        input,
      )
      return response.data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PROFILES }),
    onError: toastError,
  })
}

/** Edit a case's title, minor flag or assignee (assigned_to: null unassigns). */
export const useUpdateCase = (caseId: string) => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: Partial<CaseInput>) => {
      const response = await apiClient.patch<CaseDetail>(
        `${API}/cases/${caseId}`,
        input,
      )
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CASES })
      queryClient.invalidateQueries({ queryKey: PROFILES })
    },
    onError: toastError,
  })
}

/** Add pasted links (any text; the backend picks out the links). */
export const useAddLinks = (caseId: string) => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (text: string) => {
      const response = await apiClient.post<LinksAdded>(
        `${API}/cases/${caseId}/links`,
        { text },
      )
      return response.data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CASES }),
    onError: toastError,
  })
}

/** Remove a link from a case. */
export const useDeleteLink = (caseId: string) => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (linkId: string) => {
      await apiClient.delete(`${API}/cases/${caseId}/links/${linkId}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CASES }),
    onError: toastError,
  })
}
