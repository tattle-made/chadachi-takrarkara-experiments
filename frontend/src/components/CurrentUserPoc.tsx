import { useQuery } from "@tanstack/react-query"
import { currentUserQueryOptions } from "@/queries/user.query"

/**
 * A small POC component showing how UI can consume the current user query.
 */
export function CurrentUserPoc() {
  const {
    data: user,
    error,
    isError,
    isFetching,
    isLoading,
  } = useQuery({
    ...currentUserQueryOptions(),
    refetchInterval: 2000,
  })

  return (
    <section className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
      <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm font-medium text-slate-500">
          React Query auth POC
        </p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-950">
          Current user
        </h1>

        <div className="mt-6 rounded-md bg-slate-100 p-4 text-sm text-slate-700">
          {isLoading ? <p>Fetching user details...</p> : null}
          {!isLoading && isFetching ? <p>Refreshing user details...</p> : null}

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
            </dl>
          ) : null}

          {!isLoading && !isError && !user ? (
            <p>No logged-in user returned yet.</p>
          ) : null}
        </div>
      </div>
    </section>
  )
}
