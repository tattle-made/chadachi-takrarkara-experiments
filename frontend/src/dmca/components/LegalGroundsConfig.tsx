import * as Dialog from "@radix-ui/react-dialog"
import { useQuery } from "@tanstack/react-query"
import { Plus } from "lucide-react"
import { type FormEvent, type ReactNode, useState } from "react"
import type { LegalGround, LegalGroundInput } from "@/dmca/types"
import {
  btnLink,
  btnPrimary,
  btnSecondary,
  cardClass,
  inputClass,
  labelClass,
} from "@/dmca/ui"
import {
  legalGroundsQueryOptions,
  useCreateLegalGround,
  useDeleteLegalGround,
  useUpdateLegalGround,
} from "@/queries/dmca/config.query"

const EMPTY: LegalGroundInput = {
  title: "",
  citation: "",
  clause_text: "",
  default_selected: false,
  minor_only: false,
  active: true,
}

/** Config's legal grounds: the clauses counsellors can tick on a draft. */
export function LegalGroundsConfig() {
  const { data, isPending } = useQuery(legalGroundsQueryOptions(true))
  const grounds = data?.data ?? []

  return (
    <section>
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Legal grounds
          </h2>
          <p className="mt-0.5 text-sm text-slate-500">
            Clauses counsellors can tick on each draft.
          </p>
        </div>
        <LegalGroundDialog
          trigger={
            <button
              type="button"
              className={`${btnPrimary} inline-flex items-center gap-2`}
            >
              <Plus className="size-4" />
              New legal ground
            </button>
          }
        />
      </div>

      {isPending ? (
        <p className="text-sm text-slate-400">Loading…</p>
      ) : grounds.length === 0 ? (
        <p className="text-sm text-slate-400">No legal grounds yet.</p>
      ) : (
        <div className={`${cardClass} divide-y divide-slate-100`}>
          {grounds.map((g) => (
            <LegalGroundRow key={g.id} ground={g} />
          ))}
        </div>
      )}
    </section>
  )
}

/** One legal ground: its text and tags, with Edit, On/Off and Delete. */
function LegalGroundRow({ ground }: { ground: LegalGround }) {
  const update = useUpdateLegalGround()
  const remove = useDeleteLegalGround()

  const onDelete = () => {
    if (window.confirm(`Delete "${ground.title}"?`)) remove.mutate(ground.id)
  }

  return (
    <div
      className={`flex items-start justify-between gap-4 px-4 py-3 ${
        ground.active ? "" : "opacity-60"
      }`}
    >
      <div className="min-w-0">
        <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-slate-900">
          {ground.title}
          {ground.default_selected && <Tag>Ticked by default</Tag>}
          {ground.minor_only && <Tag>Minor cases only</Tag>}
          {!ground.active && <Tag>Off</Tag>}
        </p>
        <p className="text-xs text-slate-500">{ground.citation}</p>
        <p className="mt-1 text-sm text-slate-700">{ground.clause_text}</p>
      </div>
      <div className="flex shrink-0 gap-3">
        <LegalGroundDialog
          ground={ground}
          trigger={
            <button type="button" className={btnLink}>
              Edit
            </button>
          }
        />
        <button
          type="button"
          onClick={() =>
            update.mutate({ id: ground.id, active: !ground.active })
          }
          className={btnLink}
        >
          {ground.active ? "Turn off" : "Turn on"}
        </button>
        <button
          type="button"
          onClick={onDelete}
          className={`${btnLink} hover:text-red-600`}
        >
          Delete
        </button>
      </div>
    </div>
  )
}

/** A small grey label. */
function Tag({ children }: { children: ReactNode }) {
  return (
    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-normal text-slate-600">
      {children}
    </span>
  )
}

/** Create a legal ground, or edit one. */
function LegalGroundDialog({
  trigger,
  ground,
}: {
  trigger: ReactNode
  // edit this one; leave out to create a new one
  ground?: LegalGround
}) {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState<LegalGroundInput>(EMPTY)
  const create = useCreateLegalGround()
  const update = useUpdateLegalGround()
  const saving = create.isPending || update.isPending
  const set = (change: Partial<LegalGroundInput>) =>
    setForm((f) => ({ ...f, ...change }))
  const filled =
    form.title.trim() && form.citation.trim() && form.clause_text.trim()

  const handleOpenChange = (next: boolean) => {
    setOpen(next)
    if (next) setForm(ground ? { ...ground } : EMPTY)
  }

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!filled) return
    const input: LegalGroundInput = {
      title: form.title.trim(),
      citation: form.citation.trim(),
      clause_text: form.clause_text.trim(),
      default_selected: form.default_selected,
      minor_only: form.minor_only,
      active: form.active,
    }
    const done = { onSuccess: () => setOpen(false) }
    if (ground) update.mutate({ id: ground.id, ...input }, done)
    else create.mutate(input, done)
  }

  return (
    <Dialog.Root open={open} onOpenChange={handleOpenChange}>
      <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/30" />
        <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl">
          <Dialog.Title className="mb-4 text-lg font-semibold text-slate-900">
            {ground ? "Edit legal ground" : "New legal ground"}
          </Dialog.Title>
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label htmlFor="lgTitle" className={labelClass}>
                Title
              </label>
              <input
                id="lgTitle"
                value={form.title}
                onChange={(e) => set({ title: e.target.value })}
                placeholder="Short name shown on the draft"
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="lgCitation" className={labelClass}>
                Citation
              </label>
              <input
                id="lgCitation"
                value={form.citation}
                onChange={(e) => set({ citation: e.target.value })}
                placeholder="e.g. Section 66E, IT Act 2000"
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="lgClause" className={labelClass}>
                Clause text
              </label>
              <textarea
                id="lgClause"
                value={form.clause_text}
                onChange={(e) => set({ clause_text: e.target.value })}
                rows={4}
                placeholder="The sentence that goes into the email"
                className={inputClass}
              />
            </div>
            <div className="space-y-2 text-sm text-slate-700">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={form.default_selected}
                  onChange={(e) => set({ default_selected: e.target.checked })}
                />
                Ticked by default on new drafts
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={form.minor_only}
                  onChange={(e) => set({ minor_only: e.target.checked })}
                />
                Only on minor cases
              </label>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Dialog.Close asChild>
                <button type="button" className={btnSecondary}>
                  Cancel
                </button>
              </Dialog.Close>
              <button
                type="submit"
                disabled={!filled || saving}
                className={btnPrimary}
              >
                {saving ? "Saving…" : ground ? "Save" : "Add legal ground"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
