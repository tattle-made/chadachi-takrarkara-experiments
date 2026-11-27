import * as Dialog from "@radix-ui/react-dialog"
import { type FormEvent, type ReactNode, useState } from "react"
import type { ProfileDetail } from "@/dmca/types"
import { btnPrimary, btnSecondary, inputClass, labelClass } from "@/dmca/ui"
import {
  useCreateProfile,
  useUpdateProfile,
} from "@/queries/dmca/profiles.query"

type Props = {
  // the button that opens the dialog
  trigger: ReactNode
  // edit this profile; leave out to create a new one
  profile?: ProfileDetail
  onSaved?: (profile: ProfileDetail) => void
}

/** Create a profile, or edit one's names and notes. */
export function ProfileFormDialog({ trigger, profile, onSaved }: Props) {
  const [open, setOpen] = useState(false)
  const [fullName, setFullName] = useState("")
  const [displayName, setDisplayName] = useState("")
  const [notes, setNotes] = useState("")
  const create = useCreateProfile()
  const update = useUpdateProfile(profile?.id ?? "")
  const saving = create.isPending || update.isPending

  /** Opening fills the form from the profile (or blank); closing just closes. */
  const handleOpenChange = (next: boolean) => {
    setOpen(next)
    if (next) {
      setFullName(profile?.full_name ?? "")
      setDisplayName(profile?.display_name ?? "")
      setNotes(profile?.notes ?? "")
    }
  }

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!fullName.trim()) return
    const input = {
      full_name: fullName.trim(),
      display_name: displayName.trim() || null,
      notes: notes.trim() || null,
    }
    const done = (saved: ProfileDetail) => {
      setOpen(false)
      onSaved?.(saved)
    }
    if (profile) update.mutate(input, { onSuccess: done })
    else create.mutate(input, { onSuccess: done })
  }

  return (
    <Dialog.Root open={open} onOpenChange={handleOpenChange}>
      <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/30" />
        <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl">
          <Dialog.Title className="mb-4 text-lg font-semibold text-slate-900">
            {profile ? "Edit profile" : "New profile"}
          </Dialog.Title>
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label htmlFor="fullName" className={labelClass}>
                Full name
              </label>
              <input
                id="fullName"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className={inputClass}
                placeholder="As it should appear in the notice"
              />
            </div>
            <div>
              <label htmlFor="displayName" className={labelClass}>
                Display name (optional)
              </label>
              <input
                id="displayName"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className={inputClass}
                placeholder="Initials or a code, shown in lists instead"
              />
            </div>
            <div>
              <label htmlFor="notes" className={labelClass}>
                Notes (optional)
              </label>
              <textarea
                id="notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                className={inputClass}
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Dialog.Close asChild>
                <button type="button" className={btnSecondary}>
                  Cancel
                </button>
              </Dialog.Close>
              <button
                type="submit"
                disabled={!fullName.trim() || saving}
                className={btnPrimary}
              >
                {saving ? "Saving…" : profile ? "Save" : "Create profile"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
