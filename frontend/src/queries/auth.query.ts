import { useMutation, useQueryClient } from "@tanstack/react-query"
import apiClient from "@/lib/apiClient"
import useAuthStore from "@/stores/authStore"

type LoginCredentials = {
  email: string
  password: string
}

type LoginResponse = {
  access_token: string
  token_type: string
}

const loginFn = async (
  credentials: LoginCredentials,
): Promise<LoginResponse> => {
  const formData = new URLSearchParams()
  formData.append("username", credentials.email)
  formData.append("password", credentials.password)

  const response = await apiClient.post<LoginResponse>(
    "/api/v1/auth/login",
    formData,
    {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    },
  )
  return response.data
}

const logoutFn = async (): Promise<void> => {
  await apiClient.post("/api/v1/auth/logout")
}

export const useLoginMutation = () => {
  const { setAccessToken } = useAuthStore()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: loginFn,
    onSuccess: (data) => {
      setAccessToken(data.access_token)
      queryClient.invalidateQueries({ queryKey: ["user", "me"] })
    },
  })
}

export const useLogoutMutation = () => {
  const { clearAuth } = useAuthStore()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: logoutFn,
    onSettled: () => {
      clearAuth()
      queryClient.clear()
    },
  })
}
