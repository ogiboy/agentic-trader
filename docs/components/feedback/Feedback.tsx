'use client';

import type { FeedbackCopy } from './copy';
import { getFeedbackCopy } from './copy';
import { FeedbackResult } from './FeedbackResult';
import {
  parsePageFeedback,
  type ActionResponse,
  type FeedbackOpinion,
} from './schema';
import { Button } from '../ui/primitives/Button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '../ui/primitives/Card';
import { Textarea } from '../ui/primitives/Textarea';
import type { DocLanguage } from '../../lib/i18n/config';
import { cn } from '../../lib/utils';
import { MessageSquareText, ThumbsDown, ThumbsUp } from 'lucide-react';
import { usePathname } from 'next/navigation';
import { useState } from 'react';

const feedbackStorageKey = 'agentic-trader-docs-feedback';
const feedbackIssueUrl = 'https://github.com/ogiboy/agentic-trader/issues/new';

type ParsedPageFeedback = ReturnType<typeof parsePageFeedback>;

type FeedbackProps = Readonly<{
  locale: DocLanguage;
  title: string;
}>;

/**
 * Builds a prefilled GitHub "new issue" URL representing the provided page feedback.
 *
 * @param feedback - Parsed page feedback whose `title`, `url`, `opinion`, `submittedAt`, and `message` are included in the generated issue body
 * @returns A URL string that opens GitHub's new-issue page with the issue title and body prefilled
 */
function buildIssueUrl(feedback: ParsedPageFeedback, copy: FeedbackCopy) {
  const body = [
    '## Docs feedback',
    '',
    `Page: ${feedback.title}`,
    `URL: ${feedback.url}`,
    `Opinion: ${feedback.opinion}`,
    `Submitted at: ${feedback.submittedAt}`,
    '',
    '## Note',
    '',
    feedback.message || copy.noteFallback,
  ].join('\n');

  const params = new URLSearchParams({
    title: `Docs feedback: ${feedback.title}`,
    body,
  });

  return `${feedbackIssueUrl}?${params.toString()}`;
}

/**
 * Persists a feedback entry as a browser-local draft for later use.
 *
 * Attempts to append `feedback` to an array stored in `localStorage` under the feedback key, keeps only the most recent 25 entries, and writes the updated array back to `localStorage`.
 *
 * Storage access, JSON parse/stringify, or quota failures return `false` so the caller can surface the persistence result.
 *
 * @param feedback - The parsed page feedback object to persist as a draft
 * @returns True when the draft is stored in browser localStorage, otherwise false.
 */
function storeFeedbackDraft(feedback: ParsedPageFeedback) {
  try {
    const storage = globalThis.localStorage;
    const existing = storage.getItem(feedbackStorageKey);
    const parsed = existing ? JSON.parse(existing) : [];
    const records = Array.isArray(parsed) ? parsed : [];
    const nextRecords = [...records, feedback].slice(-25);
    storage.setItem(feedbackStorageKey, JSON.stringify(nextRecords));
    return true;
  } catch {
    return false;
  }
}

/**
 * Render a documentation feedback card that captures an opinion and an optional note, persists a draft to browser localStorage, and prepares a prefilled GitHub issue URL.
 *
 * @param locale - Locale used to select localized copy for labels and messages
 * @param title - Page title included in the saved feedback and prefilled issue
 * @returns The feedback card React element
 */
export function Feedback({ locale, title }: FeedbackProps) {
  const pathname = usePathname();
  const copy = getFeedbackCopy(locale);
  const [opinion, setOpinion] = useState<FeedbackOpinion | null>(null);
  const [message, setMessage] = useState('');
  const [result, setResult] = useState<ActionResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submitFeedback = async () => {
    if (!opinion) return;

    setIsSubmitting(true);
    try {
      const feedback = parsePageFeedback({
        opinion,
        message,
        title,
        url: pathname,
        submittedAt: new Date().toISOString(),
      });
      const stored = storeFeedbackDraft(feedback);
      setResult({
        ok: true,
        storedAt: stored ? 'browser-local-storage' : 'browser-memory',
        destination: 'github-issue',
        forwarding: 'prepared',
        githubUrl: buildIssueUrl(feedback, copy),
        warning: stored ? undefined : copy.storageWarning,
      });
      setMessage('');
    } catch (error) {
      setResult({
        ok: false,
        error: error instanceof Error ? error.message : copy.genericError,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card className='mt-10 border-border/70 bg-card/80'>
      <CardHeader>
        <CardTitle className='flex items-center gap-2 text-base'>
          <MessageSquareText data-icon='inline-start' />
          {copy.title}
        </CardTitle>
        <CardDescription>{copy.description}</CardDescription>
      </CardHeader>
      <CardContent className='flex flex-col gap-4'>
        <div className='flex flex-wrap gap-3'>
          {(['good', 'bad'] as const).map((value) => (
            <Button
              key={value}
              type='button'
              variant={opinion === value ? 'default' : 'outline'}
              onClick={() => setOpinion(value)}
            >
              {value === 'good' ? (
                <ThumbsUp data-icon='inline-start' />
              ) : (
                <ThumbsDown data-icon='inline-start' />
              )}
              {value === 'good' ? copy.helpful : copy.needsWork}
            </Button>
          ))}
        </div>
        <label className='flex flex-col gap-2 text-sm text-muted-foreground'>
          {copy.noteLabel}
          <Textarea
            className={cn(
              'min-h-28 bg-background px-3 text-sm text-foreground',
            )}
            placeholder={copy.notePlaceholder}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
          />
        </label>
      </CardContent>
      <CardFooter className='flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between'>
        <p className='text-xs text-muted-foreground'>
          {copy.destinationSummary}
        </p>
        <Button
          type='button'
          disabled={!opinion || isSubmitting}
          onClick={submitFeedback}
        >
          {isSubmitting ? copy.saving : copy.submit}
        </Button>
      </CardFooter>
      {result ? (
        <div className='border-t px-4 py-3 text-sm'>
          <FeedbackResult locale={locale} result={result} />
        </div>
      ) : null}
    </Card>
  );
}
