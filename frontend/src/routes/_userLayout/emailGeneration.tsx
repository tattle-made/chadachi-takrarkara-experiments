import { createFileRoute } from "@tanstack/react-router"
import { isAxiosError } from "axios"
import { Loader2, Send, WandSparkles } from "lucide-react"
import { type FormEvent, useState } from "react"
import { TextAnnotator } from "react-text-annotate"
import apiClient from "@/lib/apiClient"

export const Route = createFileRoute("/_userLayout/emailGeneration")({
  component: EmailGeneration,
})

const TAGS = [
  "hallucination",
  "personal-information",
  "too-verbose",
  "high-priority",
  "low-priority",
] as const

type Tag = (typeof TAGS)[number]

type AnnotationSpan = {
  start: number
  end: number
  text: string
  tag: ""
  label: Tag
  color: string
}

type FeedbackResponse = {
  feedback_id: string
}

const tagColors: Record<Tag, string> = {
  hallucination: "#ef476f",
  "personal-information": "#f7b731",
  "too-verbose": "#26de81",
  "high-priority": "#45aaf2",
  "low-priority": "#a55eea",
}

const tagLabels: Record<Tag, string> = {
  hallucination: "Hallucination",
  "personal-information": "Personal information",
  "too-verbose": "Too verbose",
  "high-priority": "High priority",
  "low-priority": "Low priority",
}

function EmailGeneration() {
  const [userQuery, setUserQuery] = useState("")
  const [generatedEmail, setGeneratedEmail] = useState("")
  const [annotations, setAnnotations] = useState<AnnotationSpan[]>([])
  const [customComment, setCustomComment] = useState("")
  const [tag, setTag] = useState<Tag>("hallucination")
  const [messageId, setMessageId] = useState<string | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false)
  const [feedbackSuccessMessage, setFeedbackSuccessMessage] = useState<
    string | null
  >(null)
  const [hasSubmittedOnce, setHasSubmittedOnce] = useState(false)
  const [isDirty, setIsDirty] = useState(true)
  const [generateError, setGenerateError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [feedbackId, setFeedbackId] = useState<string | null>(null)
  const trimmedCustomComment = customComment.trim()
  const hasFeedbackContent =
    annotations.length > 0 || trimmedCustomComment.length > 0

  const getFeedbackPayload = () => ({
    annotations: annotations.map(({ start, end, text, label }) => ({
      start,
      end,
      text,
      tag: label,
    })),
    custom_comment: trimmedCustomComment || null,
  })

  const handleGenerateEmail = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!userQuery.trim()) return

    setIsGenerating(true)
    setGeneratedEmail("")
    setAnnotations([])
    setCustomComment("")
    setMessageId(null)
    setFeedbackSubmitted(false)
    setFeedbackSuccessMessage(null)
    setHasSubmittedOnce(false)
    setIsDirty(true)
    setGenerateError(null)
    setSubmitError(null)
    setFeedbackId(null)

    try {
      const response = await apiClient.post<{
        email: string
        conversation_id: string
        message_id: string
      }>("/api/v1/email/generate", { case_details: userQuery })

      setGeneratedEmail(response.data.email)
      setMessageId(response.data.message_id)
    } catch (error) {
      if (isAxiosError(error) && !error.response) {
        setGenerateError(
          "Unable to reach the server — check your connection and try again.",
        )
      } else {
        setGenerateError("Email generation failed. Please try again.")
      }
    } finally {
      setIsGenerating(false)
    }
  }

  const handleSubmitFeedback = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!messageId) {
      setSubmitError("No email generated yet — please generate an email first.")
      return
    }
    if (!hasFeedbackContent) return

    setIsSubmitting(true)
    setSubmitError(null)
    try {
      const response = await apiClient.post<FeedbackResponse>(
        "/api/v1/email/feedback",
        {
          message_id: messageId,
          ...getFeedbackPayload(),
        },
      )
      setFeedbackSubmitted(true)
      setFeedbackSuccessMessage("Feedback submitted.")
      setHasSubmittedOnce(true)
      setIsDirty(false)
      setFeedbackId(response.data.feedback_id)
    } catch (error) {
      if (isAxiosError(error) && !error.response) {
        setSubmitError(
          "Unable to reach the server — check your connection and try again.",
        )
      } else if (isAxiosError(error) && error.response?.status === 401) {
        setSubmitError("Your session has expired. Please log in again.")
      } else {
        setSubmitError("Failed to submit feedback. Please try again.")
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleUpdateFeedback = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!feedbackId) {
      setSubmitError("No feedback found yet — please submit feedback first.")
      return
    }
    if (!hasFeedbackContent) return

    setIsSubmitting(true)
    setSubmitError(null)
    try {
      const response = await apiClient.put<FeedbackResponse>(
        `/api/v1/email/feedback/${feedbackId}`,
        getFeedbackPayload(),
      )
      setFeedbackSubmitted(true)
      setFeedbackSuccessMessage("Feedback updated.")
      setHasSubmittedOnce(true)
      setIsDirty(false)
      setFeedbackId(response.data.feedback_id)
    } catch (error) {
      if (isAxiosError(error) && !error.response) {
        setSubmitError(
          "Unable to reach the server — check your connection and try again.",
        )
      } else if (isAxiosError(error) && error.response?.status === 401) {
        setSubmitError("Your session has expired. Please log in again.")
      } else if (isAxiosError(error) && error.response?.status === 404) {
        setSubmitError("Feedback was not found. Please submit it again.")
        setFeedbackId(null)
        setHasSubmittedOnce(false)
      } else {
        setSubmitError("Failed to update feedback. Please try again.")
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      <form
        className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
        onSubmit={handleGenerateEmail}
      >
        <div>
          <label
            className="text-sm font-medium text-slate-700"
            htmlFor="user-context"
          >
            User information
          </label>
          <textarea
            className="mt-2 min-h-56 w-full resize-y rounded-md border border-slate-300 bg-white px-3 py-3 text-sm leading-6 text-slate-900 placeholder:text-slate-400 focus:border-teal-600 focus:outline-none focus:ring-1 focus:ring-teal-600"
            id="user-context"
            onChange={(event) => setUserQuery(event.target.value)}
            placeholder="Paste the full customer context here..."
            value={userQuery}
          />
        </div>

        <div className="mt-4 flex items-center gap-4">
          <button
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-slate-900 px-4 text-sm font-medium text-white hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-2 disabled:opacity-50"
            disabled={!userQuery.trim() || isGenerating}
            type="submit"
          >
            {isGenerating ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <WandSparkles className="size-4" />
            )}
            {isGenerating ? "Generating…" : "Generate email"}
          </button>
          {generateError && (
            <p className="text-sm text-red-600">{generateError}</p>
          )}
        </div>
      </form>

      {generatedEmail && (
        <form
          className="space-y-4"
          onSubmit={feedbackId ? handleUpdateFeedback : handleSubmitFeedback}
        >
          <div className="grid gap-4 lg:grid-cols-[minmax(0,3fr)_260px]">
            <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
              <h1 className="text-base font-semibold text-slate-900">
                Generated email
              </h1>
              <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-4 text-sm leading-7 text-slate-900">
                <TextAnnotator
                  content={generatedEmail}
                  getSpan={(span) => ({
                    ...span,
                    tag: "" as const,
                    label: tag,
                    color: tagColors[tag],
                  })}
                  onChange={(newValue) => {
                    setAnnotations(newValue as AnnotationSpan[])
                    setFeedbackSubmitted(false)
                    setFeedbackSuccessMessage(null)
                    setIsDirty(true)
                    setSubmitError(null)
                  }}
                  style={{ whiteSpace: "pre-wrap" }}
                  value={annotations}
                />
              </div>
            </div>

            <aside className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-900">
                Annotation type
              </h2>
              <div className="mt-3 space-y-2">
                {TAGS.map((tagName) => (
                  <label
                    className="flex min-h-10 items-center gap-3 rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700 has-[:checked]:border-slate-900 has-[:checked]:bg-slate-50"
                    key={tagName}
                  >
                    <input
                      checked={tag === tagName}
                      className="sr-only"
                      name="annotation-type"
                      onChange={() => setTag(tagName)}
                      type="radio"
                    />
                    <span
                      aria-hidden="true"
                      className="size-3 shrink-0 rounded-full"
                      style={{ backgroundColor: tagColors[tagName] }}
                    />
                    <span className="font-medium">{tagLabels[tagName]}</span>
                  </label>
                ))}
              </div>

              <div className="mt-4 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">
                <span className="font-medium text-slate-900">
                  {annotations.length}
                </span>{" "}
                annotations selected
              </div>
            </aside>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <label
              className="text-sm font-medium text-slate-700"
              htmlFor="custom-comment"
            >
              Additional remarks
            </label>
            <textarea
              className="mt-2 min-h-28 w-full resize-y rounded-md border border-slate-300 bg-white px-3 py-3 text-sm leading-6 text-slate-900 placeholder:text-slate-400 focus:border-teal-600 focus:outline-none focus:ring-1 focus:ring-teal-600"
              id="custom-comment"
              onChange={(event) => {
                setCustomComment(event.target.value)
                setFeedbackSubmitted(false)
                setFeedbackSuccessMessage(null)
                setIsDirty(true)
                setSubmitError(null)
              }}
              placeholder="Add any extra feedback for the generated email..."
              value={customComment}
            />
          </div>

          <div className="flex items-center gap-4">
            <button
              className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-teal-700 px-4 text-sm font-medium text-white hover:bg-teal-800 focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-2 disabled:opacity-50"
              disabled={isSubmitting || !isDirty || !hasFeedbackContent}
              type="submit"
            >
              <Send className="size-4" />
              {isSubmitting
                ? feedbackId
                  ? "Updating…"
                  : "Submitting…"
                : hasSubmittedOnce
                  ? "Update feedback"
                  : "Submit feedback"}
            </button>
            {feedbackSubmitted && feedbackSuccessMessage && (
              <p className="text-sm text-teal-700">{feedbackSuccessMessage}</p>
            )}
            {submitError && (
              <p className="text-sm text-red-600">{submitError}</p>
            )}
          </div>
        </form>
      )}
    </div>
  )
}
