import { zodResolver } from "@hookform/resolvers/zod"
import * as Dialog from "@radix-ui/react-dialog"
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"
import apiClient from "@/lib/apiClient"
import {
  useArchiveUserMutation,
  useCreateUserMutation,
  usersQueryOptions,
  useUnarchiveUserMutation,
} from "@/queries/users.query"
import type { User } from "@/types/user.type"

export const Route = createFileRoute("/_userLayout/admin/")({
  beforeLoad: async () => {
    try {
      const response = await apiClient.get("/api/v1/users/me")
      if (response.data.role !== "admin") {
        throw redirect({ to: "/" })
      }
    } catch (err) {
      if (err instanceof Error && "isRedirect" in err) throw err
      throw redirect({ to: "/" })
    }
  },
  component: AdminUsersPage,
})

const createUserSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Must be at least 8 characters"),
  role: z.enum(["admin", "manager", "member"]),
})

type CreateUserValues = z.infer<typeof createUserSchema>

const ROLE_BADGE: Record<string, string> = {
  admin: "bg-purple-50 text-purple-700",
  manager: "bg-blue-50 text-blue-700",
  member: "bg-slate-100 text-slate-700",
}

function AdminUsersPage() {
  const [addOpen, setAddOpen] = useState(false)
  const [archiveTarget, setArchiveTarget] = useState<User | null>(null)
  const [isExporting, setIsExporting] = useState(false)

  const handleExportCsv = async () => {
    setIsExporting(true)
    try {
      const response = await apiClient.get("/api/v1/email/feedback/export", {
        responseType: "blob",
      })
      const url = URL.createObjectURL(
        new Blob([response.data], { type: "text/csv" }),
      )
      const link = document.createElement("a")
      link.href = url
      link.download = "feedback_export.csv"
      link.click()
      URL.revokeObjectURL(url)
    } finally {
      setIsExporting(false)
    }
  }

  const { data, isLoading } = useQuery(usersQueryOptions())
  const {
    mutate: createUser,
    isPending: isCreating,
    error: createError,
    reset: resetCreate,
  } = useCreateUserMutation()
  const { mutate: archiveUser, isPending: isArchiving } =
    useArchiveUserMutation()
  const { mutate: unarchiveUser } = useUnarchiveUserMutation()

  const {
    register,
    handleSubmit,
    reset: resetForm,
    formState: { errors },
  } = useForm<CreateUserValues>({
    resolver: zodResolver(createUserSchema),
    defaultValues: { role: "member" },
  })

  const activeUsers = data?.data.filter((u) => u.is_active) ?? []
  const archivedUsers = data?.data.filter((u) => !u.is_active) ?? []

  const handleAddOpenChange = (next: boolean) => {
    setAddOpen(next)
    if (!next) {
      resetForm()
      resetCreate()
    }
  }

  const onCreateSubmit = (values: CreateUserValues) => {
    createUser(values, { onSuccess: () => handleAddOpenChange(false) })
  }

  const confirmArchive = () => {
    if (!archiveTarget) return
    archiveUser(archiveTarget.id, { onSettled: () => setArchiveTarget(null) })
  }

  return (
    <div className="space-y-10">
      {/* ── Active users ─────────────────────────────── */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">
              Active users
            </h1>
            {!isLoading && (
              <p className="mt-0.5 text-sm text-slate-500">
                {activeUsers.length} total
              </p>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleExportCsv}
              disabled={isExporting}
              className="rounded-md border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              {isExporting ? "Exporting…" : "Export feedback CSV"}
            </button>

            <Dialog.Root open={addOpen} onOpenChange={handleAddOpenChange}>
              <Dialog.Trigger asChild>
                <button
                  type="button"
                  className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
                >
                  Add user
                </button>
              </Dialog.Trigger>
              <Dialog.Portal>
                <Dialog.Overlay className="fixed inset-0 bg-black/30" />
                <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl">
                  <Dialog.Title className="mb-4 text-lg font-semibold text-slate-900">
                    Add user
                  </Dialog.Title>
                  <form
                    onSubmit={handleSubmit(onCreateSubmit)}
                    className="space-y-4"
                    noValidate
                  >
                    <div>
                      <label
                        htmlFor="email"
                        className="block text-sm font-medium text-slate-700"
                      >
                        Email
                      </label>
                      <input
                        id="email"
                        type="email"
                        autoComplete="off"
                        {...register("email")}
                        className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-slate-500"
                        placeholder="user@example.com"
                      />
                      {errors.email && (
                        <p className="mt-1 text-xs text-red-600">
                          {errors.email.message}
                        </p>
                      )}
                    </div>
                    <div>
                      <label
                        htmlFor="password"
                        className="block text-sm font-medium text-slate-700"
                      >
                        Password
                      </label>
                      <input
                        id="password"
                        type="password"
                        autoComplete="new-password"
                        {...register("password")}
                        className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-slate-500"
                        placeholder="••••••••"
                      />
                      {errors.password && (
                        <p className="mt-1 text-xs text-red-600">
                          {errors.password.message}
                        </p>
                      )}
                    </div>
                    <div>
                      <label
                        htmlFor="role"
                        className="block text-sm font-medium text-slate-700"
                      >
                        Role
                      </label>
                      <select
                        id="role"
                        {...register("role")}
                        className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-slate-500"
                      >
                        <option value="member">Member</option>
                        <option value="manager">Manager</option>
                        <option value="admin">Admin</option>
                      </select>
                    </div>
                    {createError && (
                      <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
                        {createError instanceof Error
                          ? createError.message
                          : "Failed to create user"}
                      </p>
                    )}
                    <div className="flex justify-end gap-3 pt-2">
                      <Dialog.Close asChild>
                        <button
                          type="button"
                          className="rounded-md border border-slate-200 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
                        >
                          Cancel
                        </button>
                      </Dialog.Close>
                      <button
                        type="submit"
                        disabled={isCreating}
                        className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
                      >
                        {isCreating ? "Adding…" : "Add user"}
                      </button>
                    </div>
                  </form>
                </Dialog.Content>
              </Dialog.Portal>
            </Dialog.Root>
          </div>
        </div>

        {isLoading ? (
          <p className="text-sm text-slate-500">Loading users…</p>
        ) : activeUsers.length === 0 ? (
          <p className="text-sm text-slate-400">No active users.</p>
        ) : (
          <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-4 py-3 text-left font-medium text-slate-500">
                    Email
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-slate-500">
                    Role
                  </th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {activeUsers.map((user) => (
                  <tr
                    key={user.id}
                    className="border-b border-slate-100 last:border-0"
                  >
                    <td className="px-4 py-3 text-slate-900">{user.email}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ${ROLE_BADGE[user.role] ?? ROLE_BADGE.member}`}
                      >
                        {user.role}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => setArchiveTarget(user)}
                        className="text-xs text-slate-400 hover:text-red-600 underline underline-offset-2"
                      >
                        Archive
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ── Archived users ───────────────────────────── */}
      {!isLoading && archivedUsers.length > 0 && (
        <section>
          <div className="mb-4">
            <h2 className="text-base font-semibold text-slate-500">
              Archived users
            </h2>
            <p className="mt-0.5 text-sm text-slate-400">
              {archivedUsers.length} total
            </p>
          </div>
          <div className="overflow-hidden rounded-lg border border-slate-200 bg-white opacity-75">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-4 py-3 text-left font-medium text-slate-400">
                    Email
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-slate-400">
                    Role
                  </th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {archivedUsers.map((user) => (
                  <tr
                    key={user.id}
                    className="border-b border-slate-100 last:border-0"
                  >
                    <td className="px-4 py-3 text-slate-400 line-through">
                      {user.email}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize bg-slate-100 text-slate-400">
                        {user.role}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => unarchiveUser(user.id)}
                        className="text-xs text-slate-400 hover:text-slate-700 underline underline-offset-2"
                      >
                        Unarchive
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* ── Archive confirmation dialog ───────────────── */}
      <Dialog.Root
        open={!!archiveTarget}
        onOpenChange={(open) => {
          if (!open) setArchiveTarget(null)
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/30" />
          <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl">
            <Dialog.Title className="text-base font-semibold text-slate-900">
              Archive user?
            </Dialog.Title>
            <p className="mt-2 text-sm text-slate-500">
              <span className="font-medium text-slate-700">
                {archiveTarget?.email}
              </span>{" "}
              will be moved to the archived list and will no longer be able to
              sign in.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="rounded-md border border-slate-200 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
              </Dialog.Close>
              <button
                type="button"
                onClick={confirmArchive}
                disabled={isArchiving}
                className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
              >
                {isArchiving ? "Archiving…" : "Archive"}
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  )
}
