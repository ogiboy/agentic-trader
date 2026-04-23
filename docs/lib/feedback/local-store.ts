import { appendFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const feedbackDir = resolve(repoRoot, "runtime");

export const feedbackFile = resolve(feedbackDir, "docs-feedback.jsonl");

export async function appendFeedbackRecord(
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
