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

function isToolActionKind(value: unknown): value is ToolActionKind {
  return typeof value === 'string' && SUPPORTED_TOOL_ACTIONS.has(value as ToolActionKind);
}

function toolActionCooldownMs(kind: ToolActionKind): number {
  if (kind === 'enable-local-tools') {
    return 1_000;
  }
  return 5_000;
}

/**
 * Handle local-tool helper actions from the Web GUI.
 *
 * Supported actions are allowlisted and delegate to existing CLI lifecycle
 * contracts. They do not generate secrets, fetch browser binaries, pull models,
 * or start the trading daemon.
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
