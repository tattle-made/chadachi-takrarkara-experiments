import { createFileRoute, redirect } from "@tanstack/react-router";
import { Send, WandSparkles } from "lucide-react";
import { type FormEvent, useState } from "react";
import { TextAnnotator } from "react-text-annotate";
import apiClient from "@/lib/apiClient";
import useAuthStore from "@/stores/authStore";

export const Route = createFileRoute("/emailGeneration")({
  beforeLoad: async () => {
    const { accessToken, setAccessToken } = useAuthStore.getState();
    if (accessToken) return;

    try {
      const response = await apiClient.post("/api/v1/auth/refresh");
      setAccessToken(response.data.access_token);
    } catch {
      throw redirect({ to: "/login" });
    }
  },
  component: EmailGeneration,
});

const MOCK_EMAIL = `Subject: Urgent Request for Removal of Non-Consensual Intimate Images of jane Jaseniah on Instagram Greetings from RATI Foundation. We are reaching out to report an extremely distressing incident involving Jane Doe, who has been the victim of non-consensual sharing of her intimate images on Instagram. jane became aware on this date, via a friend, that nude images originally shared privately during a past relationship were uploaded to pornographic websites without her consent, causing her significant psychological distress and a deep fear for her privacy, safety, and dignity. Nature of Abuse: jane’s private nude images, taken during a consensual relationship that ended in 2024, have been shared non-consensually on Instagram and subsequently posted to explicit sites, triggering severe emotional distress and reputational damage. jane proactively reached out to us, and she has also contacted the websites directly for takedown. The unauthorized sharing of such intimate material inflicts ongoing harm on her wellbeing and sense of safety. Meta Community Guideline Violations Involved:
Adult Sexual Exploitation / Non-Consensual Intimate Images (NCII):
 "We remove images that depict incidents of sexual violence and intimate images shared without the consent of the person(s) pictured... We do not allow:
Sharing, threatening, stating an intent to share, offering or asking for non-consensual intimate imagery (NCII) that fulfils all of the three following conditions:
Imagery is non-commercial and produced in a private setting.
Person in the imagery is (near) nude, engaged in sexual activity or in a sexually suggestive pose.
Lack of consent to share the imagery is indicated by meeting any of the signals: vengeful context, independent sources (such as law enforcement records, media reports, or representatives of a survivor), or report from the person depicted."
 —Meta Community Standards, Adult Sexual Exploitation
Privacy Violations:
 "Privacy gives people the freedom to be themselves... We remove content that could contribute to a risk of harm to the physical security of persons. Content that threatens people has the potential to intimidate, exclude or silence others and isn't allowed on our services... We may remove: A reported photo or video of people where... an adult, where the content was reported by the adult from outside the United States and applicable law may provide rights to removal." —Meta Community Standards, Privacy Violations
Dignity and Safety:
 "We expect that people will respect the dignity of others and not harass or degrade others. We remove content that could contribute to a risk of harm to the physical security of persons."
 —Meta Community Standards, Main Page
Closing Remark / Request:
This situation constitutes a grave violation of Meta’s policies, particularly concerning non-consensual intimate image (NCII). We respectfully and urgently request the immediate removal of all offending content connected to jane Jaseniah’s images and the disabling of accounts responsible for this distribution. Her continued exposure to this harmful content is causing severe ongoing trauma. We are ready to provide any additional information if required to support this process. Thank you for your urgent attention and support in protecting the privacy, dignity, and psychological safety of the victim. Best regards,
RATI Foundation
`;

const TAGS = [
  "hallucination",
  "personal-information",
  "too-verbose",
  "high-priority",
  "low-priority",
  "others",
] as const;

type Tag = (typeof TAGS)[number];

type AnnotationSpan = {
  start: number;
  end: number;
  text: string;
  tag: "";
  label: Tag;
  color: string;
};

const tagColors: Record<Tag, string> = {
  hallucination: "#ef476f",
  "personal-information": "#f7b731",
  "too-verbose": "#26de81",
  "high-priority": "#45aaf2",
  "low-priority": "#a55eea",
  others: "#94a3b8",
};

const tagLabels: Record<Tag, string> = {
  hallucination: "Hallucination",
  "personal-information": "Personal information",
  "too-verbose": "Too verbose",
  "high-priority": "High priority",
  "low-priority": "Low priority",
  others: "Others",
};

function EmailGeneration() {
  const [userQuery, setUserQuery] = useState("");
  const [generatedEmail, setGeneratedEmail] = useState("");
  const [annotations, setAnnotations] = useState<AnnotationSpan[]>([]);
  const [customComment, setCustomComment] = useState("");
  const [tag, setTag] = useState<Tag>("hallucination");

  const handleGenerateEmail = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!userQuery.trim()) return;

    setGeneratedEmail(MOCK_EMAIL);
    setAnnotations([]);
    setCustomComment("");
  };

  const handleSubmitFeedback = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const feedbackBody = {
      text: generatedEmail,
      annotations: annotations.map(({ start, end, text, label, color }) => ({
        start,
        end,
        text,
        tag: label,
        color,
      })),
      customComment,
    };

    console.log("email annotation feedback", feedbackBody);
  };

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

        <div className="mt-4 flex justify-start">
          <button
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-slate-900 px-4 text-sm font-medium text-white hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-2 disabled:opacity-50"
            disabled={!userQuery.trim()}
            type="submit"
          >
            <WandSparkles className="size-4" />
            Generate email
          </button>
        </div>
      </form>

      {generatedEmail && (
        <form className="space-y-4" onSubmit={handleSubmitFeedback}>
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
                    setAnnotations(newValue as AnnotationSpan[]);
                  }}
                  style={{
                    whiteSpace: "pre-wrap",
                  }}
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
              onChange={(event) => setCustomComment(event.target.value)}
              placeholder="Add any extra feedback for the generated email..."
              value={customComment}
            />
          </div>

          <div className="flex justify-start">
            <button
              className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-teal-700 px-4 text-sm font-medium text-white hover:bg-teal-800 focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-2"
              type="submit"
            >
              <Send className="size-4" />
              Submit feedback
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
