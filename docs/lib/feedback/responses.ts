import type { ActionResponse } from "@/components/feedback/schema";

export function localOnlyResponse(
  forwarding: "disabled" | "failed",
  warning?: string,
): ActionResponse {
  return {
    ok: true,
    destination: "local-log",
    forwarding,
    storedAt: "runtime/docs-feedback.jsonl",
    warning,
  };
}
