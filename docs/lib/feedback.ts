import { appendFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  blockFeedback,
  pageFeedback,
  type ActionResponse,
  type BlockFeedbackInput,
  type PageFeedbackInput,
} from "@/components/feedback/schema";
import {
  isGithubFeedbackConfigured,
  onBlockFeedbackAction as onGitHubBlockFeedbackAction,
  onPageFeedbackAction as onGitHubPageFeedbackAction,
} from "@/lib/github";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const feedbackDir = resolve(repoRoot, "runtime");
const feedbackFile = resolve(feedbackDir, "docs-feedback.jsonl");

async function appendFeedbackRecord(
  kind: "page" | "block",
  feedback: Record<string, unknown>,
) {
  await mkdir(feedbackDir, { recursive: true });
  await appendFile(
    feedbackFile,
    `${JSON.stringify({
      kind,
      ...feedback,
    })}\n`,
    "utf8",
  );
}

export async function onPageFeedbackAction(
  input: PageFeedbackInput,
): Promise<ActionResponse> {
  "use server";

  try {
    const feedback = pageFeedback.parse(input);
    await appendFeedbackRecord("page", feedback);

    if (!isGithubFeedbackConfigured()) {
      return {
        ok: true,
        destination: "local-log",
        storedAt: "runtime/docs-feedback.jsonl",
        warning:
          "Saved locally only. Configure docs/.env.local with GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY to forward into GitHub Discussions.",
      };
    }

    try {
      const response = await onGitHubPageFeedbackAction(feedback);
      if (response.ok) {
        return response;
      }

      return {
        ok: true,
        destination: "local-log",
        storedAt: "runtime/docs-feedback.jsonl",
        warning: `Saved locally because GitHub forwarding failed: ${response.error}`,
      };
    } catch (error) {
      return {
        ok: true,
        destination: "local-log",
        storedAt: "runtime/docs-feedback.jsonl",
        warning: `Saved locally because GitHub forwarding failed: ${
          error instanceof Error
            ? error.message
            : "Unknown GitHub feedback error."
        }`,
      };
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
      return {
        ok: true,
        destination: "local-log",
        storedAt: "runtime/docs-feedback.jsonl",
        warning:
          "Saved locally only. Configure docs/.env.local with GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY to forward into GitHub Discussions.",
      };
    }

    try {
      const response = await onGitHubBlockFeedbackAction(feedback);
      if (response.ok) {
        return response;
      }

      return {
        ok: true,
        destination: "local-log",
        storedAt: "runtime/docs-feedback.jsonl",
        warning: `Saved locally because GitHub forwarding failed: ${response.error}`,
      };
    } catch (error) {
      return {
        ok: true,
        destination: "local-log",
        storedAt: "runtime/docs-feedback.jsonl",
        warning: `Saved locally because GitHub forwarding failed: ${
          error instanceof Error
            ? error.message
            : "Unknown GitHub feedback error."
        }`,
      };
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
