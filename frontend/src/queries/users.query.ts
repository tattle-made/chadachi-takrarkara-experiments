import {
  queryOptions,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query"
import apiClient from "@/lib/apiClient"
import type { User, UserRole } from "@/types/user.type"

type UsersResponse = {
  data: User[]
  count: number
}

type CreateUserPayload = {
  email: string
  password: string
  role: UserRole
  is_active?: boolean
}

export const usersQueryOptions = () =>
  queryOptions({
    queryKey: ["users"],
    queryFn: async () => {
      const response = await apiClient.get<UsersResponse>("/api/v1/users/")
      return response.data
    },
  })

export const useCreateUserMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: CreateUserPayload) => {
      const response = await apiClient.post<User>("/api/v1/users/", payload)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })
}

export const useChangePasswordMutation = () =>
  useMutation({
    mutationFn: async (payload: {
      current_password: string
      new_password: string
    }) => {
      await apiClient.patch("/api/v1/users/me/password", payload)
    },
  })

export const useArchiveUserMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (userId: number) => {
      await apiClient.patch(`/api/v1/users/${userId}/archive`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  })
}

export const useUnarchiveUserMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (userId: number) => {
      await apiClient.patch(`/api/v1/users/${userId}/unarchive`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  })
}
