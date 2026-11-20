// Tailwind class strings shared across preview screens (same look as admin/).
export const btnPrimary =
  "rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
export const btnSecondary =
  "rounded-md border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
export const btnLink =
  "text-xs text-slate-500 underline underline-offset-2 hover:text-slate-900"
// fieldBase has no width so callers can set one; inputBase is full width.
export const fieldBase =
  "block rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-slate-500"
export const inputBase = `w-full ${fieldBase}`
export const inputClass = `mt-1 ${inputBase}`
export const labelClass = "block text-sm font-medium text-slate-700"
export const cardClass = "rounded-lg border border-slate-200 bg-white"
export const thClass = "px-4 py-3 text-left font-medium text-slate-500"
export const tdClass = "px-4 py-3 align-top"

export const formatDate = (iso: string) =>
  new Date(iso).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  })
