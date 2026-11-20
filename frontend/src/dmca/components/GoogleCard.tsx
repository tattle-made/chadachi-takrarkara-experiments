import { useQuery } from "@tanstack/react-query"
import { CheckCircle2, XCircle } from "lucide-react"
import { btnPrimary, btnSecondary, cardClass, formatDate } from "@/dmca/ui"
import {
  googleStatusQueryOptions,
  useConnectGoogle,
  useDisconnectGoogle,
} from "@/queries/dmca/config.query"

/** The Google account emails are sent from: status, connect, disconnect. */
export function GoogleCard() {
  const { data: google, isPending } = useQuery(googleStatusQueryOptions())
  const connect = useConnectGoogle()
  const disconnect = useDisconnectGoogle()

  const onDisconnect = () => {
    if (
      window.confirm(
        "Disconnect Google? Emails can't be sent and documents can't be uploaded until it's connected again.",
      )
    ) {
      disconnect.mutate()
    }
  }

  return (
    <section>
      <h2 className="mb-3 text-base font-semibold text-slate-900">
        Google account
      </h2>
      <div
        className={`${cardClass} flex flex-wrap items-center justify-between gap-4 p-4`}
      >
        {isPending || !google ? (
          <p className="text-sm text-slate-400">Checking…</p>
        ) : google.connected ? (
          <div className="flex items-start gap-2 text-sm">
            <CheckCircle2 className="mt-0.5 size-4 text-emerald-600" />
            <div>
              <p className="font-medium text-slate-900">
                Connected as {google.account_email}
              </p>
              {google.connected_at && (
                <p className="text-xs text-slate-500">
                  Since {formatDate(google.connected_at)}
                </p>
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-start gap-2 text-sm">
            <XCircle className="mt-0.5 size-4 text-red-600" />
            <div>
              <p className="font-medium text-slate-900">
                {google.status === "broken"
                  ? `The connection to ${google.account_email} stopped working`
                  : "Not connected"}
              </p>
              <p className="text-xs text-slate-500">
                Emails are sent from this account and documents are kept in its
                Drive.
              </p>
              {google.last_error && (
                <p className="mt-0.5 text-xs text-red-700">
                  {google.last_error}
                </p>
              )}
            </div>
          </div>
        )}

        {google && (
          <div className="flex gap-2">
            {google.status && (
              <button
                type="button"
                onClick={onDisconnect}
                disabled={disconnect.isPending}
                className={btnSecondary}
              >
                Disconnect
              </button>
            )}
            {!google.connected && (
              <button
                type="button"
                onClick={() => connect.mutate()}
                disabled={connect.isPending}
                className={btnPrimary}
              >
                {google.status === "broken" ? "Reconnect" : "Connect Google"}
              </button>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
