import { useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useEffect } from "react"
import { toast } from "sonner"
import { GoogleCard } from "@/dmca/components/GoogleCard"
import { LegalGroundsConfig } from "@/dmca/components/LegalGroundsConfig"
import { RecipientsConfig } from "@/dmca/components/RecipientsConfig"
import { googleStatusQueryOptions } from "@/queries/dmca/config.query"
import { currentUserQueryOptions } from "@/queries/user.query"

export const Route = createFileRoute("/_userLayout/dmca/config")({
  // Google sends the browser back here with ?google=connected or
  // ?google=error&reason=...
  validateSearch: (
    search: Record<string, unknown>,
  ): { google?: string; reason?: string } => ({
    google: typeof search.google === "string" ? search.google : undefined,
    reason: typeof search.reason === "string" ? search.reason : undefined,
  }),
  component: ConfigPage,
})

/** Admin settings: the Google account, recipients, and legal grounds. */
function ConfigPage() {
  const { data: user, isPending } = useQuery(currentUserQueryOptions())
  const { google, reason } = Route.useSearch()
  const navigate = Route.useNavigate()
  const queryClient = useQueryClient()

  // after coming back from Google: say how it went, then clean the URL
  useEffect(() => {
    if (!google) return
    // a fixed id, so the toast shows once even if this runs twice
    const id = "google-callback"
    if (google === "connected") toast.success("Google connected", { id })
    else
      toast.error(`Couldn't connect Google: ${reason ?? "unknown error"}`, {
        id,
      })
    queryClient.invalidateQueries({
      queryKey: googleStatusQueryOptions().queryKey,
    })
    navigate({ search: {}, replace: true })
  }, [google, reason, navigate, queryClient])

  if (isPending) return <p className="text-sm text-slate-400">Loading…</p>
  if (user?.role !== "admin") {
    return <p className="text-sm text-slate-500">Config is for admins only.</p>
  }

  return (
    <div className="space-y-12">
      <GoogleCard />
      <RecipientsConfig />
      <LegalGroundsConfig />
    </div>
  )
}
