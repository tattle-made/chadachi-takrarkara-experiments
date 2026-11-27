import { isAxiosError } from "axios"
import { toast } from "sonner"

/** The backend's message for a failed request ("detail"), or a fallback. */
export function errorMessage(err: unknown): string {
  if (isAxiosError(err)) {
    const detail = err.response?.data?.detail
    if (typeof detail === "string") return detail
    // a 422 lists what was wrong with each field
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg
    if (!err.response) return "Couldn't reach the server. Try again."
  }
  return "Something went wrong. Try again."
}

/** Show a failed request's message as a toast (used as a mutation's onError). */
export function toastError(err: unknown) {
  toast.error(errorMessage(err))
}
