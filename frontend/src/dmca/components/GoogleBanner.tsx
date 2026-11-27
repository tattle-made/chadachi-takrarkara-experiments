import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { AlertTriangle } from "lucide-react"
import { googleStatusQueryOptions } from "@/queries/dmca/config.query"

/** A red bar on every DMCA page while Google isn't connected (or the
 * connection broke), since sending and uploads can't work without it. */
export function GoogleBanner({ isAdmin }: { isAdmin: boolean }) {
  const {
    data: google,
    refetch,
    isFetching,
  } = useQuery(googleStatusQueryOptions())
  if (!google || google.connected) return null

  return (
    <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      <AlertTriangle className="mt-0.5 size-4 shrink-0" />
      <div className="flex-1">
        <p className="font-medium">
          {google.status === "broken"
            ? "The Google connection stopped working."
            : "Google isn't connected."}{" "}
          Emails can't be sent and documents can't be uploaded.
        </p>
        {google.last_error && (
          <p className="mt-0.5 text-xs text-red-700">{google.last_error}</p>
        )}
        <p className="mt-1 text-xs">
          {isAdmin ? (
            <Link to="/dmca/config" className="underline underline-offset-2">
              Connect Google in Config
            </Link>
          ) : (
            "Ask an admin to connect it in Config."
          )}
        </p>
      </div>
      <button
        type="button"
        onClick={() => refetch()}
        disabled={isFetching}
        className="text-xs underline underline-offset-2 disabled:opacity-50"
      >
        {isFetching ? "Checking…" : "Check again"}
      </button>
    </div>
  )
}
