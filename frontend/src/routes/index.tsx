import { createFileRoute, redirect } from "@tanstack/react-router"
import { CurrentUserPoc } from "@/components/CurrentUserPoc"
import apiClient from "@/lib/apiClient"
import useAuthStore from "@/stores/authStore"

export const Route = createFileRoute("/")({
  beforeLoad: async () => {
    const { accessToken, setAccessToken } = useAuthStore.getState()
    if (accessToken) return
    try {
      const response = await apiClient.post("/api/v1/auth/refresh")
      setAccessToken(response.data.access_token)
    } catch {
      throw redirect({ to: "/login" })
    }
  },
  component: Index,
})

function Index() {
  return <CurrentUserPoc />
}
