import type { ActionResponse } from "@/components/feedback/schema";
import type { DocLanguage } from "@/lib/i18n/config";
import { getFeedbackCopy } from "@/components/feedback/copy";

type FeedbackResultProps = {
  locale: DocLanguage;
  result: ActionResponse;
};

export function FeedbackResult({
  locale,
  result,
}: Readonly<FeedbackResultProps>) {
  const copy = getFeedbackCopy(locale);

  if (!result.ok) {
    return <p className="text-destructive">{result.error}</p>;
  }

  const message =
    result.forwarding === "succeeded"
      ? copy.successForwarded
      : result.forwarding === "failed"
        ? copy.successLocalOnlyFailed
        : copy.successLocalOnlyDisabled;

  return (
    <div className="flex flex-col gap-2">
      <p className="text-primary">{message}</p>
      {result.githubUrl ? (
        <a
          className="text-sm text-primary underline underline-offset-4"
          href={result.githubUrl}
          rel="noopener noreferrer"
          target="_blank"
        >
          {copy.openDiscussion}
        </a>
      ) : null}
      {result.warning ? (
        <p className="text-muted-foreground">
          <span className="font-medium text-foreground">{copy.technicalDetail}:</span>{" "}
          {result.warning}
        </p>
      ) : null}
    </div>
  );
}
