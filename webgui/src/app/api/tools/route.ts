import { runToolAction, type ToolActionKind } from '../../../lib/agentic-trader';
import {
  beginRequestGuard,
  parseJsonObjectBody,
  redactAndCapText,
  rejectUnsafeWebguiRequest,
} from '../../../lib/http';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const SUPPORTED_TOOL_ACTIONS = new Set<ToolActionKind>([
  'enable-local-tools',
  'enable-host-fallbacks',
  'start-model-service',
  'start-camofox-service',
]);

/**
 * Determines whether a value is a supported ToolActionKind.
 *
 * @param value - The value to test for membership in the supported tool action allowlist
 * @returns `true` if `value` is one of the supported `ToolActionKind` values, `false` otherwise.
 */
function isToolActionKind(value: unknown): value is ToolActionKind {
  return typeof value === 'string' && SUPPORTED_TOOL_ACTIONS.has(value as ToolActionKind);
}

/**
 * Get the cooldown duration in milliseconds for a given tool action kind.
 *
 * @param kind - The tool action kind to evaluate
 * @returns `1000` for `enable-local-tools`, `5000` for all other supported kinds
 */
function toolActionCooldownMs(kind: ToolActionKind): number {
  if (kind === 'enable-local-tools') {
    return 1_000;
  }
  return 5_000;
}

/**
 * Handles Web GUI tool actions by validating the request, enforcing per-action throttling, and executing an allowlisted tool action.
 *
 * @param request - HTTP request whose JSON body must include a `kind` property set to one of the supported tool action kinds.
 * @returns A JSON Response containing the action result; returns a 400 JSON response for an invalid `kind` or a 500 JSON response with a redacted error message on internal failure.
 */
export async function POST(request: Request) {
  const unsafeResponse = rejectUnsafeWebguiRequest(request, {
    requireJson: true,
  });
  if (unsafeResponse) {
    return unsafeResponse;
  }

  const parsed = await parseJsonObjectBody(request, { maxBytes: 8 * 1024 });
  if (!parsed.ok) {
    return parsed.response;
  }
  const body = parsed.body;

  try {
    if (!isToolActionKind(body.kind)) {
      return Response.json({ error: 'invalid tool action' }, { status: 400 });
    }
    const guard = beginRequestGuard({
      key: 'tools',
      cooldownMs: toolActionCooldownMs(body.kind),
      singleFlight: true,
    });
    if (!guard.ok) {
      return guard.response;
    }
    try {
      const result = await runToolAction(body.kind);
      return Response.json(result);
    } finally {
      guard.release();
    }
  } catch (error) {
    return Response.json({ error: redactAndCapText(error) }, { status: 500 });
  }
}
