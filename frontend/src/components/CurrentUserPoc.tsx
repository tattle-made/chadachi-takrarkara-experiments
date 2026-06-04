import { zodResolver } from "@hookform/resolvers/zod"
import * as Dialog from "@radix-ui/react-dialog"
import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { useLogoutMutation } from "@/queries/auth.query"
import { currentUserQueryOptions } from "@/queries/user.query"
import { useChangePasswordMutation } from "@/queries/users.query"

const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, "Required"),
    new_password: z.string().min(8, "Must be at least 8 characters"),
    confirm_password: z.string().min(1, "Required"),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  })

type ChangePasswordValues = z.infer<typeof changePasswordSchema>

export function CurrentUserPoc() {
  const [open, setOpen] = useState(false)
  const {
    data: user,
    error,
    isError,
    isLoading,
  } = useQuery(currentUserQueryOptions())
  const { mutate: logout, isPending: isLoggingOut } = useLogoutMutation()
  const {
    mutate: changePassword,
    isPending: isChanging,
    error: changeError,
    reset: resetMutation,
  } = useChangePasswordMutation()
  const navigate = useNavigate()

  const {
    register,
    handleSubmit,
    reset: resetForm,
    formState: { errors },
  } = useForm<ChangePasswordValues>({
    resolver: zodResolver(changePasswordSchema),
  })

  const handleOpenChange = (next: boolean) => {
    setOpen(next)
    if (!next) {
      resetForm()
      resetMutation()
    }
  }

  const onSubmit = (values: ChangePasswordValues) => {
    changePassword(
      {
        current_password: values.current_password,
        new_password: values.new_password,
      },
      { onSuccess: () => handleOpenChange(false) },
    )
  }

  const handleLogout = () => {
    logout(undefined, { onSettled: () => navigate({ to: "/login" }) })
  }

  return (
    <section className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
      <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-500">Signed in as</p>
            <h1 className="mt-1 text-2xl font-semibold text-slate-950">
              Current user
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <Dialog.Root open={open} onOpenChange={handleOpenChange}>
              <Dialog.Trigger asChild>
                <button
                  type="button"
                  className="rounded-md border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
                >
                  Change password
                </button>
              </Dialog.Trigger>
              <Dialog.Portal>
                <Dialog.Overlay className="fixed inset-0 bg-black/30" />
                <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl">
                  <Dialog.Title className="mb-4 text-lg font-semibold text-slate-900">
                    Change password
                  </Dialog.Title>
                  <form
                    onSubmit={handleSubmit(onSubmit)}
                    className="space-y-4"
                    noValidate
                  >
                    {(
                      [
                        [
                          "current_password",
                          "Current password",
                          "current-password",
                        ],
                        ["new_password", "New password", "new-password"],
                        [
                          "confirm_password",
                          "Confirm new password",
                          "new-password",
                        ],
                      ] as const
                    ).map(([field, label, autocomplete]) => (
                      <div key={field}>
                        <label
                          htmlFor={field}
                          className="block text-sm font-medium text-slate-700"
                        >
                          {label}
                        </label>
                        <input
                          id={field}
                          type="password"
                          autoComplete={autocomplete}
                          {...register(field)}
                          className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-slate-500"
                          placeholder="••••••••"
                        />
                        {errors[field] && (
                          <p className="mt-1 text-xs text-red-600">
                            {errors[field]?.message}
                          </p>
                        )}
                      </div>
                    ))}
                    {changeError && (
                      <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
                        {changeError instanceof Error
                          ? changeError.message
                          : "Failed to update password"}
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
                        disabled={isChanging}
                        className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
                      >
                        {isChanging ? "Saving…" : "Save"}
                      </button>
                    </div>
                  </form>
                </Dialog.Content>
              </Dialog.Portal>
            </Dialog.Root>
            <button
              type="button"
              onClick={handleLogout}
              disabled={isLoggingOut}
              className="rounded-md border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50"
            >
              {isLoggingOut ? "Signing out…" : "Sign out"}
            </button>
          </div>
        </div>

        <div className="mt-6 rounded-md bg-slate-100 p-4 text-sm text-slate-700">
          {isLoading ? <p>Fetching user details...</p> : null}
          {isError ? (
            <p>
              User request failed:{" "}
              {error instanceof Error ? error.message : "Unknown error"}
            </p>
          ) : null}
          {!isLoading && !isError && user ? (
            <dl className="space-y-2">
              <div>
                <dt className="font-medium text-slate-500">ID</dt>
                <dd className="text-slate-950">{user.id}</dd>
              </div>
              <div>
                <dt className="font-medium text-slate-500">Email</dt>
                <dd className="text-slate-950">{user.email}</dd>
              </div>
              <div>
                <dt className="font-medium text-slate-500">Role</dt>
                <dd className="capitalize text-slate-950">{user.role}</dd>
              </div>
            </dl>
          ) : null}
        </div>
      </div>
    </section>
  )
}
