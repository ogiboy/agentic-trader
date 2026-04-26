export type FeedbackOpinion = 'good' | 'bad';

export type PageFeedbackInput = {
  opinion: FeedbackOpinion;
  message?: string;
  title?: string;
  url: string;
  submittedAt?: string;
};

export type PageFeedback = {
  opinion: FeedbackOpinion;
  message: string;
  title: string;
  url: string;
  submittedAt: string;
};

export type BlockFeedbackInput = PageFeedbackInput & {
  blockId: string;
  blockBody?: string;
};

export type BlockFeedback = PageFeedback & {
  blockId: string;
  blockBody?: string;
};

export type ActionResponse =
  | {
      ok: true;
      storedAt: string;
      destination: 'github-discussion' | 'github-issue' | 'local-log';
      forwarding: 'succeeded' | 'prepared' | 'disabled' | 'failed';
      githubUrl?: string;
      warning?: string;
    }
  | {
      ok: false;
      error: string;
      storedAt?: string;
    };

const FEEDBACK_OPINIONS = new Set<FeedbackOpinion>(['good', 'bad']);

function assertString(value: unknown, field: string) {
  if (typeof value !== 'string') {
    throw new TypeError(`${field} must be a string`);
  }

  return value.trim();
}

export function parsePageFeedback(input: PageFeedbackInput): PageFeedback {
  if (!FEEDBACK_OPINIONS.has(input.opinion)) {
    throw new Error('opinion must be either good or bad');
  }

  const url = assertString(input.url, 'url');
  if (!url) {
    throw new Error('url is required');
  }

  const title = typeof input.title === 'string' ? input.title.trim() : '';
  const message = typeof input.message === 'string' ? input.message.trim() : '';
  const submittedAt =
    typeof input.submittedAt === 'string' && input.submittedAt.trim()
      ? input.submittedAt.trim()
      : new Date().toISOString();

  return {
    opinion: input.opinion,
    message: message.slice(0, 2000),
    title: title || 'Untitled page',
    url,
    submittedAt,
  };
}

export function parseBlockFeedback(input: BlockFeedbackInput): BlockFeedback {
  const feedback = parsePageFeedback(input);
  const blockId = assertString(input.blockId, 'blockId');

  if (!blockId) {
    throw new Error('blockId is required');
  }

  const blockBody =
    typeof input.blockBody === 'string' ? input.blockBody.trim() : undefined;

  return {
    ...feedback,
    blockId,
    blockBody: blockBody ? blockBody.slice(0, 4000) : undefined,
  };
}

export const pageFeedback = {
  parse: parsePageFeedback,
};

export const blockFeedback = {
  parse: parseBlockFeedback,
};
