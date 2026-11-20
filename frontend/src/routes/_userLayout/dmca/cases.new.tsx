import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { type FormEvent, useState } from "react"
import { ProfileDocsNote } from "@/dmca/components/DocumentsPanel"
import { btnPrimary, cardClass, inputClass, labelClass } from "@/dmca/ui"
import {
  profileQueryOptions,
  useCreateCase,
} from "@/queries/dmca/profiles.query"
import { currentUserQueryOptions } from "@/queries/user.query"

export const Route = createFileRoute("/_userLayout/dmca/cases/new")({
  validateSearch: (search: Record<string, unknown>) => ({
    profileId: String(search.profileId ?? ""),
  }),
  component: NewCasePage,
})

/** Create a case for a profile, then go to it to paste links. */
function NewCasePage() {
  const { profileId } = Route.useSearch()
  const navigate = useNavigate()
  const { data: profile, isPending } = useQuery({
    ...profileQueryOptions(profileId),
    enabled: Boolean(profileId),
  })
  const { data: me } = useQuery(currentUserQueryOptions())
  const createCase = useCreateCase(profileId)
  const [title, setTitle] = useState("")
  const [isMinor, setIsMinor] = useState(false)

  if (profileId && isPending) {
    return <p className="text-sm text-slate-400">Loading…</p>
  }
  if (!profile) {
    return (
      <p className="text-sm text-slate-500">
        Pick a profile first.{" "}
        <Link to="/dmca" className="underline">
          Back to profiles
        </Link>
      </p>
    )
  }

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!title.trim()) return
    createCase.mutate(
      // whoever creates the case is its owner to begin with
      { title: title.trim(), is_minor: isMinor, assigned_to: me?.id ?? null },
      {
        onSuccess: (created) =>
          navigate({
            to: "/dmca/cases/$caseId",
            params: { caseId: created.id },
          }),
      },
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <Link
          to="/dmca/profiles/$profileId"
          params={{ profileId }}
          className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900"
        >
          <ArrowLeft className="size-4" />
          {profile.full_name}
        </Link>
        <h1 className="text-xl font-semibold text-slate-900">New case</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          One case per incident. Next you paste all the links, and the app
          splits them into one email per recipient.
        </p>
      </div>

      <form onSubmit={onSubmit} className={`${cardClass} space-y-5 p-6`}>
        <div>
          <label htmlFor="title" className={labelClass}>
            Case title
          </label>
          <input
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Video leak – Oct 2026"
            className={inputClass}
          />
        </div>

        <label className="flex items-start gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={isMinor}
            onChange={(e) => setIsMinor(e.target.checked)}
            className="mt-0.5"
          />
          <span>
            The person is a minor (under 18)
            <span className="block text-xs text-slate-500">
              Emails use the CSAM wording and go to CSAM addresses first. Add an
              age proof document to the profile.
            </span>
          </span>
        </label>

        <ProfileDocsNote profileId={profileId} />

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={!title.trim() || createCase.isPending}
            className={btnPrimary}
          >
            {createCase.isPending ? "Creating…" : "Create case"}
          </button>
        </div>
      </form>
    </div>
  )
}
