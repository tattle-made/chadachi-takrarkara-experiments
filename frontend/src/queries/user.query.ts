import { queryOptions } from "@tanstack/react-query"
import apiClient from "@/lib/apiClient"
import type { User } from "@/types/user.type"

const fetchCurrentUser = async (): Promise<User> => {
  const response = await apiClient.get<User>("/api/v1/users/me")
  return response.data
}

export const currentUserQueryOptions = () =>
  queryOptions({
    queryKey: ["user", "me"],
    queryFn: fetchCurrentUser,
    staleTime: 60_000,
    retry: false,
  })
