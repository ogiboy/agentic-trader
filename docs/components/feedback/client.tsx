"use client";

import { useState, useTransition } from "react";
import { usePathname } from "next/navigation";
import { MessageSquareText, ThumbsDown, ThumbsUp } from "lucide-react";
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

type FeedbackProps = {
  title: string;
  onSendAction: (feedback: PageFeedbackInput) => Promise<ActionResponse>;
};

const opinionCopy: Record<FeedbackOpinion, string> = {
  good: "Helpful",
  bad: "Needs work",
};

export function Feedback({ title, onSendAction }: FeedbackProps) {
  const pathname = usePathname();
  const [opinion, setOpinion] = useState<FeedbackOpinion | null>(null);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<ActionResponse | null>(null);
  const [isPending, startTransition] = useTransition();

  const submitFeedback = () => {
    if (!opinion) return;

    startTransition(() => {
      void onSendAction({
        opinion,
        message,
        title,
        url: pathname,
        submittedAt: new Date().toISOString(),
      })
        .then((response) => {
          setResult(response);

          if (response.ok) {
            setMessage("");
          }
        })
        .catch((error) => {
          setResult({
            ok: false,
            error:
              error instanceof Error
                ? error.message
                : "Failed to send feedback.",
          });
        });
    });
  };

  return (
    <Card className="mt-10 border-border/70 bg-card/80">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <MessageSquareText data-icon="inline-start" />
          How was this page?
        </CardTitle>
        <CardDescription>
          Feedback is mirrored into a local log for this checkout and forwards
          into GitHub Discussions when the docs app credentials are configured
          in <code>docs/.env.local</code>.
        </CardDescription>
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
              {opinionCopy[value]}
            </Button>
          ))}
        </div>
        <label className="flex flex-col gap-2 text-sm text-muted-foreground">
          Optional note
          <textarea
            className={cn(
              "min-h-28 rounded-none border border-input bg-background px-3 py-2 text-sm text-foreground",
              "outline-none transition-all focus-visible:border-ring focus-visible:ring-1 focus-visible:ring-ring/50",
            )}
            placeholder="Tell us what was clear, missing, or confusing."
            value={message}
            onChange={(event) => setMessage(event.target.value)}
          />
        </label>
      </CardContent>
      <CardFooter className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-muted-foreground">
          Local mirror: `runtime/docs-feedback.jsonl`
        </p>
        <Button
          type="button"
          disabled={!opinion || isPending}
          onClick={submitFeedback}
        >
          {isPending ? "Saving feedback..." : "Send feedback"}
        </Button>
      </CardFooter>
      {result ? (
        <div className="border-t px-4 py-3 text-sm">
          {result.ok ? (
            <div className="flex flex-col gap-2">
              <p className="text-primary">
                {result.destination === "github-discussion"
                  ? "Thanks. Saved locally and forwarded to GitHub Discussions."
                  : `Thanks. Saved locally to ${result.storedAt}.`}
              </p>
              {result.githubUrl ? (
                <a
                  className="text-sm text-primary underline underline-offset-4"
                  href={result.githubUrl}
                  rel="noreferrer"
                  target="_blank"
                >
                  Open GitHub discussion
                </a>
              ) : null}
              {result.warning ? (
                <p className="text-muted-foreground">{result.warning}</p>
              ) : null}
            </div>
          ) : (
            <p className="text-destructive">{result.error}</p>
          )}
        </div>
      ) : null}
    </Card>
  );
}
