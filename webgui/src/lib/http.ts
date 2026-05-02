import { timingSafeEqual } from 'node:crypto';

export type JsonObjectBodyResult =
  | { ok: true; body: Record<string, unknown> }
  | { ok: false; response: Response };

type ParseJsonOptions = {
  maxBytes?: number;
};

type RequestGuardOptions = {
  cooldownMs?: number;
  key: string;
  singleFlight?: boolean;
};

type RequestGuardResult =
  | { ok: true; release: () => void }
  | { ok: false; response: Response };

const DEFAULT_MAX_JSON_BODY_BYTES = 32 * 1024;
const SAFE_METHODS_WITHOUT_BROWSER_ORIGIN = new Set(['GET', 'HEAD', 'OPTIONS']);
const SECRET_ASSIGNMENT_PATTERN =
  /\b([A-Z0-9_.-]*(?:API[_-]?KEY|SECRET|TOKEN|PASSWORD)[A-Z0-9_.-]*)(\s*[:=]\s*)([^\s,;"']+)/gi;
const BEARER_PATTERN = /\bBearer\s+[A-Za-z0-9._~+/=-]+/gi;
const AUTHORIZATION_PATTERN =
  /\b(Authorization)(\s*[:=]\s*)(?!Bearer\s)([^\s,;"']+)/gi;
const URL_SECRET_PATTERN =
  /([?&](?:api[_-]?key|apikey|token|secret|password|key)=)[^&\s]+/gi;
const inFlightRequests = new Set<string>();
const cooldownUntilByKey = new Map<string, number>();

function jsonError(
  error: string,
  status: number,
  headers?: HeadersInit,
): Response {
  return Response.json({ error }, { status, headers });
}

function configuredWebguiToken(): null | string {
  const token = process.env.AGENTIC_TRADER_WEBGUI_TOKEN?.trim();
  return token || null;
}

function constantTimeEqual(left: string, right: string): boolean {
  const leftBuffer = Buffer.from(left);
  const rightBuffer = Buffer.from(right);
  if (leftBuffer.length !== rightBuffer.length) {
    return false;
  }
  return timingSafeEqual(leftBuffer, rightBuffer);
}

function bearerToken(value: null | string): null | string {
  const prefix = 'Bearer ';
  if (!value?.startsWith(prefix)) {
    return null;
  }
  return value.slice(prefix.length).trim() || null;
}

function isLoopbackHostname(hostname: string): boolean {
  const normalized = hostname.toLowerCase().replace(/^\[|\]$/g, '');
  return (
    normalized === 'localhost' ||
    normalized === '127.0.0.1' ||
    normalized === '::1' ||
    normalized.endsWith('.localhost')
  );
}

function isAuthorizedWebguiRequest(request: Request): boolean {
  const token = configuredWebguiToken();
  const requestUrl = new URL(request.url);
  if (!token) {
    return isLoopbackHostname(requestUrl.hostname);
  }
  const provided =
    request.headers.get('x-agentic-trader-token') ||
    bearerToken(request.headers.get('authorization')) ||
    '';
  return constantTimeEqual(provided, token);
}

export function isSameOriginRequest(request: Request): boolean {
  const requestOrigin = new URL(request.url).origin;
  const origin = request.headers.get('origin');
  if (origin) {
    return origin === requestOrigin;
  }
  const referer = request.headers.get('referer');
  if (!referer) {
    return SAFE_METHODS_WITHOUT_BROWSER_ORIGIN.has(
      request.method.toUpperCase(),
    );
  }
  try {
    return new URL(referer).origin === requestOrigin;
  } catch {
    return false;
  }
}

export function rejectUnsafeWebguiRequest(
  request: Request,
  { requireJson }: { requireJson: boolean },
): null | Response {
  if (!isAuthorizedWebguiRequest(request)) {
    return jsonError('unauthorized', 401);
  }
  if (!isSameOriginRequest(request)) {
    return jsonError('forbidden origin', 403);
  }
  if (requireJson) {
    const contentType = request.headers.get('content-type')?.toLowerCase() || '';
    if (!contentType.includes('application/json')) {
      return jsonError('expected application/json', 400);
    }
  }
  return null;
}

export function beginRequestGuard({
  cooldownMs = 0,
  key,
  singleFlight = false,
}: RequestGuardOptions): RequestGuardResult {
  const now = Date.now();
  const cooldownUntil = cooldownUntilByKey.get(key) || 0;
  if (cooldownUntil > now) {
    const retryAfterSeconds = Math.max(
      1,
      Math.ceil((cooldownUntil - now) / 1000),
    );
    return {
      ok: false,
      response: jsonError('rate limited', 429, {
        'Retry-After': String(retryAfterSeconds),
      }),
    };
  }
  if (singleFlight && inFlightRequests.has(key)) {
    return {
      ok: false,
      response: jsonError('request already running', 409, {
        'Retry-After': '1',
      }),
    };
  }
  if (singleFlight) {
    inFlightRequests.add(key);
  }
  return {
    ok: true,
    release: () => {
      if (singleFlight) {
        inFlightRequests.delete(key);
      }
      if (cooldownMs > 0) {
        cooldownUntilByKey.set(key, Date.now() + cooldownMs);
      }
    },
  };
}

export function redactAndCapText(value: unknown, maxLength = 2_000): string {
  let text = value instanceof Error ? value.message : String(value);
  text = text.replace(SECRET_ASSIGNMENT_PATTERN, '$1$2<redacted>');
  text = text.replace(BEARER_PATTERN, 'Bearer <redacted>');
  text = text.replace(AUTHORIZATION_PATTERN, '$1$2<redacted>');
  text = text.replace(URL_SECRET_PATTERN, '$1<redacted>');
  if (text.length > maxLength) {
    return `${text.slice(0, maxLength)}...<truncated>`;
  }
  return text;
}

export async function parseJsonObjectBody(
  request: Request,
  { maxBytes = DEFAULT_MAX_JSON_BODY_BYTES }: ParseJsonOptions = {},
): Promise<JsonObjectBodyResult> {
  const contentLength = Number(request.headers.get('content-length') || 0);
  if (Number.isFinite(contentLength) && contentLength > maxBytes) {
    return {
      ok: false,
      response: jsonError('request body too large', 413),
    };
  }
  try {
    const rawBody = await request.text();
    if (new TextEncoder().encode(rawBody).byteLength > maxBytes) {
      return {
        ok: false,
        response: jsonError('request body too large', 413),
      };
    }
    const parsed: unknown = JSON.parse(rawBody);
    if (
      typeof parsed !== 'object' ||
      parsed === null ||
      Array.isArray(parsed)
    ) {
      return {
        ok: false,
        response: jsonError('invalid json', 400),
      };
    }
    return { ok: true, body: parsed as Record<string, unknown> };
  } catch {
    return {
      ok: false,
      response: jsonError('invalid json', 400),
    };
  }
}
