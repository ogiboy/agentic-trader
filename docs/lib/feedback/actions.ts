import {
  blockFeedback,
  pageFeedback,
  type ActionResponse,
  type BlockFeedbackInput,
  type PageFeedbackInput,
} from "@/components/feedback/schema";
import { createDiscussionThread } from "@/lib/feedback/github-discussions";
import { isGithubFeedbackConfigured } from "@/lib/feedback/github-config";
import { appendFeedbackRecord } from "@/lib/feedback/local-store";
import { localOnlyResponse } from "@/lib/feedback/responses";

function buildPageDiscussionBody(
  opinion: string,
  title: string,
  message: string,
) {
  return `[${opinion}] ${title}\n\n${message || "No additional note provided."}\n\n> Forwarded from docs page feedback.`;
}

function buildBlockDiscussionBody(
  blockBody: string,
  opinion: string,
  message: string,
) {
  return `> ${blockBody}\n\n[${opinion}] ${message || "No additional note provided."}\n\n> Forwarded from docs block feedback.`;
}

export async function onPageFeedbackAction(
  input: PageFeedbackInput,
): Promise<ActionResponse> {
  "use server";

  try {
    const feedback = pageFeedback.parse(input);
    await appendFeedbackRecord("page", feedback);

    if (!isGithubFeedbackConfigured()) {
      return localOnlyResponse(
        "disabled",
        "Saved to the local feedback log only. Configure docs/.env.local with GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY to also forward into GitHub Discussions.",
      );
    }

    try {
      return await createDiscussionThread(
        feedback.url,
        buildPageDiscussionBody(
          feedback.opinion,
          feedback.title,
          feedback.message,
        ),
      );
    } catch (error) {
      return localOnlyResponse(
        "failed",
        `Saved locally because GitHub forwarding failed: ${
          error instanceof Error
            ? error.message
            : "Unknown GitHub feedback error."
        }`,
      );
    }
  } catch (error) {
    return {
      ok: false,
      error:
        error instanceof Error
          ? error.message
          : "Failed to store docs feedback.",
    };
  }
}

export async function onBlockFeedbackAction(
  input: BlockFeedbackInput,
): Promise<ActionResponse> {
  "use server";

  try {
    const feedback = blockFeedback.parse(input);
    await appendFeedbackRecord("block", feedback);

    if (!isGithubFeedbackConfigured()) {
      return localOnlyResponse(
        "disabled",
        "Saved to the local feedback log only. Configure docs/.env.local with GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY to also forward into GitHub Discussions.",
      );
    }

    try {
      return await createDiscussionThread(
        feedback.url,
        buildBlockDiscussionBody(
          feedback.blockBody ?? feedback.blockId,
          feedback.opinion,
          feedback.message,
        ),
      );
    } catch (error) {
      return localOnlyResponse(
        "failed",
        `Saved locally because GitHub forwarding failed: ${
          error instanceof Error
            ? error.message
            : "Unknown GitHub feedback error."
        }`,
      );
    }
  } catch (error) {
    return {
      ok: false,
      error:
        error instanceof Error
          ? error.message
          : "Failed to store docs feedback.",
    };
  }
}
