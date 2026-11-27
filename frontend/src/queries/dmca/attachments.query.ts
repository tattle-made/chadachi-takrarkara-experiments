// A profile's documents (stored in Google Drive by the backend).
import {
  queryOptions,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query"
import { toastError } from "@/dmca/errors"
import type { Attachment, AttachmentKind } from "@/dmca/types"
import apiClient from "@/lib/apiClient"

const API = "/api/v1/dmca"
const ATTACHMENTS = ["dmca", "attachments"] as const

/** A profile's documents. */
export const attachmentsQueryOptions = (profileId: string) =>
  queryOptions({
    queryKey: [...ATTACHMENTS, profileId],
    queryFn: async () => {
      const response = await apiClient.get<Attachment[]>(
        `${API}/profiles/${profileId}/attachments`,
      )
      return response.data
    },
  })

/** Upload a document to a profile (stored in Drive). */
export const useUploadAttachment = (profileId: string) => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      kind,
      file,
    }: {
      kind: AttachmentKind
      file: File
    }) => {
      const form = new FormData()
      form.append("kind", kind)
      form.append("file", file)
      const response = await apiClient.post<Attachment>(
        `${API}/profiles/${profileId}/attachments`,
        form,
      )
      return response.data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ATTACHMENTS }),
    onError: toastError,
  })
}

/** Download a document. A plain link can't be used: the request needs the
 * login token, so the file is fetched here and then saved from memory. */
export async function downloadAttachment(attachment: Attachment) {
  try {
    const response = await apiClient.get<Blob>(
      `${API}/attachments/${attachment.id}/file`,
      { responseType: "blob" },
    )
    const url = URL.createObjectURL(response.data)
    const link = document.createElement("a")
    link.href = url
    link.download = attachment.file_name
    link.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    toastError(err)
  }
}
