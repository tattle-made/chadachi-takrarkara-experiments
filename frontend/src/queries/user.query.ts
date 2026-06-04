import { queryOptions } from "@tanstack/react-query"
import type { User } from "@/types/user.type"

const fetchCurrentUser = async (): Promise<User | null> => {
  // API Call

  await new Promise((resolve) => setTimeout(resolve, 1000))

  const random = Math.random()
  if (random < 0.5) {
    return null
  }

  return {
    id: 1,
    email: "dummyuser@abc.com",
  }
}

/**
 * A POC React Query option for fetching the current logged-in user.
 *
 * For now, fetchCurrentUser returns a dummy user after a short delay. In the real
 * auth flow, this queryFn can call an API ex: /backend/me with HTTP-only cookie auth.
 *
 * Usage in a JSX component:
 function CurrentUser() {
  const { data: user, isLoading, isError } = useQuery(currentUserQueryOptions())

  if (isLoading) return <p>Loading user...</p>
  if (isError) return <p>Failed to load user.</p>
  if (!user) return <p>No logged-in user.</p>

  return <p>{user.email}</p>
}
 */
export const currentUserQueryOptions = () =>
  queryOptions({
    queryKey: ["user", "me"],
    queryFn: fetchCurrentUser,
    staleTime: 1000,
  })
