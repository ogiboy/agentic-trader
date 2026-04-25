"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { MessageSquareText, ThumbsDown, ThumbsUp } from "lucide-react";
import { getFeedbackCopy } from "@/components/feedback/copy";
import { FeedbackResult } from "@/components/feedback/feedback-result";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type {
  ActionResponse,
  FeedbackOpinion,
  PageFeedbackInput,
} from "@/components/feedback/schema";
import type { DocLanguage } from "@/lib/i18n/config";

type FeedbackProps = {
  locale: DocLanguage;
  title: string;
  onSendAction: (feedback: PageFeedbackInput) => Promise<ActionResponse>;
};

export function Feedback({ locale, title, onSendAction }: FeedbackProps) {
  const pathname = usePathname();
  const copy = getFeedbackCopy(locale);
  const [opinion, setOpinion] = useState<FeedbackOpinion | null>(null);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<ActionResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submitFeedback = async () => {
    if (!opinion) return;

    setIsSubmitting(true);
    try {
      const response = await onSendAction({
        opinion,
        message,
        title,
        url: pathname,
        submittedAt: new Date().toISOString(),
      });
      setResult(response);

      if (response.ok) {
        setMessage("");
      }
    } catch (error) {
      setResult({
        ok: false,
        error:
          error instanceof Error
            ? error.message
            : copy.genericError,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card className="mt-10 border-border/70 bg-card/80">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <MessageSquareText data-icon="inline-start" />
          {copy.title}
        </CardTitle>
        <CardDescription>{copy.description}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-wrap gap-3">
          {(["good", "bad"] as const).map((value) => (
            <Button
              key={value}
              type="button"
              variant={opinion === value ? "default" : "outline"}
              onClick={() => setOpinion(value)}
            >
              {value === "good" ? (
                <ThumbsUp data-icon="inline-start" />
              ) : (
                <ThumbsDown data-icon="inline-start" />
              )}
              {value === "good" ? copy.helpful : copy.needsWork}
            </Button>
          ))}
        </div>
        <label className="flex flex-col gap-2 text-sm text-muted-foreground">
          {copy.noteLabel}
          <textarea
            className={cn(
              "min-h-28 rounded-none border border-input bg-background px-3 py-2 text-sm text-foreground",
              "outline-none transition-all focus-visible:border-ring focus-visible:ring-1 focus-visible:ring-ring/50",
            )}
            placeholder={copy.notePlaceholder}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
          />
        </label>
      </CardContent>
      <CardFooter className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-muted-foreground">{copy.destinationSummary}</p>
        <Button
          type="button"
          disabled={!opinion || isSubmitting}
          onClick={submitFeedback}
        >
          {isSubmitting ? copy.saving : copy.submit}
        </Button>
      </CardFooter>
      {result ? (
        <div className="border-t px-4 py-3 text-sm">
          <FeedbackResult locale={locale} result={result} />
        </div>
      ) : null}
    </Card>
  );
}
