import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { type FormEvent, useState } from "react"
import { AddLinksFlow } from "@/preview/components/AddLinksFlow"
import { ProfileDocsNote } from "@/preview/components/DocumentsPanel"
import {
  btnPrimary,
  cardClass,
  inputClass,
  labelClass,
} from "@/preview/components/ui"
import { usePreviewStore } from "@/preview/store"

export const Route = createFileRoute("/_userLayout/dmca/cases/new")({
  validateSearch: (search: Record<string, unknown>) => ({
    profileId: String(search.profileId ?? ""),
  }),
  component: NewCasePage,
})

function NewCasePage() {
  const { profileId } = Route.useSearch()
  const navigate = useNavigate()
  const state = usePreviewStore()
  const profile = state.profiles.find((p) => p.id === profileId)

  const [title, setTitle] = useState("")
  const [caseId, setCaseId] = useState<string | null>(null)

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

  const onContinue = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!title.trim()) return
    setCaseId(state.addCase({ profileId, title: title.trim() }))
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
          {profile.fullName}
        </Link>
        <h1 className="text-xl font-semibold text-slate-900">New case</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          One case per incident. All the links go in together, and the app
          splits them into one email per recipient.
        </p>
      </div>

      {/* ── Step 1: details ────────────────────── */}
      <section className={`${cardClass} p-6`}>
        <h2 className="mb-4 text-sm font-semibold text-slate-900">
          1. Case details
        </h2>
        {caseId ? (
          <div className="text-sm text-slate-600">
            <p className="font-medium text-slate-900">{title}</p>
          </div>
        ) : (
          <form onSubmit={onContinue} className="space-y-5">
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

            <ProfileDocsNote profileId={profileId} />

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={!title.trim()}
                className={btnPrimary}
              >
                Continue to links
              </button>
            </div>
          </form>
        )}
      </section>

      {/* ── Step 2: links → review → drafts ────── */}
      <section className={`${cardClass} p-6 ${caseId ? "" : "opacity-50"}`}>
        <h2 className="mb-4 text-sm font-semibold text-slate-900">
          2. Links and recipients
        </h2>
        {caseId ? (
          <AddLinksFlow
            caseId={caseId}
            onDone={() =>
              navigate({
                to: "/dmca/cases/$caseId",
                params: { caseId },
              })
            }
          />
        ) : (
          <p className="text-sm text-slate-400">Add the case details first.</p>
        )}
      </section>
    </div>
  )
}
