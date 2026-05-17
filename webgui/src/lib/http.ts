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
  /\b([A-Z0-9_.-]*(?:API[_-]?KEY|ACCESS[_-]?KEY|SECRET|TOKEN|PASSWORD)[A-Z0-9_.-]*)(\s*[:=]\s*)([^\s,;"']+)/gi;
const JSON_SECRET_PATTERN =
  /("[^"]*(?:api[_-]?key|access[_-]?key|secret|token|password)[^"]*"\s*:\s*")([^"]+)(")/gi;
const SECRET_ENV_NAME_PATTERN =
  /(?:API[_-]?KEY|ACCESS[_-]?KEY|SECRET|TOKEN|PASSWORD)/i;
const BEARER_PATTERN = /\bBearer\s+[a-z0-9._~+/=-]+/gi;
const AUTHORIZATION_PATTERN =
  /\b(Authorization)(\s*[:=]\s*)(?!Bearer\s)([^\s,;"']+)/gi;
const URL_SECRET_PATTERN =
  /([?&](?:api[_-]?key|token|secret|password|key)=)[^&\s]+/gi;
const inFlightRequests = new Set<string>();
const cooldownUntilByKey = new Map<string, number>();

export const WEBGUI_SESSION_COOKIE_NAME = 'agentic_trader_webgui_session';

function jsonError(
  error: string,
  status: number,
  headers?: HeadersInit,
): Response {
  return Response.json({ error }, { status, headers });
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, String.raw`\$&`);
}

function sensitiveEnvValues(): string[] {
  return Object.entries(process.env)
    .filter(([key, value]) => SECRET_ENV_NAME_PATTERN.test(key) && Boolean(value))
    .map(([, value]) => String(value))
    .filter((value) => value.length >= 4)
    .sort((left, right) => right.length - left.length);
}

export function configuredWebguiToken(): null | string {
  const token = process.env.AGENTIC_TRADER_WEBGUI_TOKEN?.trim();
  return token || null;
}

function tokenlessLoopbackModeEnabled(): boolean {
  return process.env.AGENTIC_TRADER_WEBGUI_LOOPBACK_ONLY === '1';
}

export function constantTimeEqual(left: string, right: string): boolean {
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
  const normalized = hostname.toLowerCase().replaceAll(/^\[|\]$/g, '');
  return (
    normalized === 'localhost' ||
    normalized === '127.0.0.1' ||
    normalized === '::1' ||
    normalized.endsWith('.localhost')
  );
}

function originPort(url: URL): string {
  if (url.port) {
    return url.port;
  }
  if (url.protocol === 'https:') {
    return '443';
  }
  if (url.protocol === 'http:') {
    return '80';
  }
  return '';
}

function isEquivalentSameOrigin(left: URL, right: URL): boolean {
  if (left.origin === right.origin) {
    return true;
  }
  return (
    left.protocol === right.protocol &&
    originPort(left) === originPort(right) &&
    isLoopbackHostname(left.hostname) &&
    isLoopbackHostname(right.hostname)
  );
}

function cookieValue(request: Request, cookieName: string): null | string {
  const rawCookie = request.headers.get('cookie');
  if (!rawCookie) {
    return null;
  }
  for (const chunk of rawCookie.split(';')) {
    const [name, ...valueParts] = chunk.trim().split('=');
    if (name !== cookieName) {
      continue;
    }
    const rawValue = valueParts.join('=');
    if (!rawValue) {
      return null;
    }
    try {
      return decodeURIComponent(rawValue);
    } catch {
      return rawValue;
    }
  }
  return null;
}

export function isAuthorizedWebguiRequest(request: Request): boolean {
  const token = configuredWebguiToken();
  const requestUrl = new URL(request.url);
  if (!token) {
    return (
      tokenlessLoopbackModeEnabled() && isLoopbackHostname(requestUrl.hostname)
    );
  }
  const provided =
    request.headers.get('x-agentic-trader-token') ||
    bearerToken(request.headers.get('authorization')) ||
    cookieValue(request, WEBGUI_SESSION_COOKIE_NAME) ||
    '';
  return constantTimeEqual(provided, token);
}

export function isSameOriginRequest(request: Request): boolean {
  const requestUrl = new URL(request.url);
  const origin = request.headers.get('origin');
  if (origin) {
    try {
      return isEquivalentSameOrigin(new URL(origin), requestUrl);
    } catch {
      return false;
    }
  }
  const referer = request.headers.get('referer');
  if (!referer) {
    return SAFE_METHODS_WITHOUT_BROWSER_ORIGIN.has(
      request.method.toUpperCase(),
    );
  }
  try {
    return isEquivalentSameOrigin(new URL(referer), requestUrl);
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
    const contentType =
      request.headers.get('content-type')?.toLowerCase() || '';
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

export function resetRequestGuardsForTests(): void {
  inFlightRequests.clear();
  cooldownUntilByKey.clear();
}

export function redactAndCapText(value: unknown, maxLength = 2_000): string {
  let text = value instanceof Error ? value.message : String(value);
  for (const secret of sensitiveEnvValues()) {
    text = text.replaceAll(new RegExp(escapeRegExp(secret), 'g'), '<redacted>');
  }
  text = text.replaceAll(JSON_SECRET_PATTERN, '$1<redacted>$3');
  text = text.replaceAll(SECRET_ASSIGNMENT_PATTERN, '$1$2<redacted>');
  text = text.replaceAll(BEARER_PATTERN, 'Bearer <redacted>');
  text = text.replaceAll(AUTHORIZATION_PATTERN, '$1$2<redacted>');
  text = text.replaceAll(URL_SECRET_PATTERN, '$1<redacted>');
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
    const reader = request.body?.getReader();
    let rawBody = '';
    if (reader) {
      const decoder = new TextDecoder();
      let receivedBytes = 0;
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }
        receivedBytes += value.byteLength;
        if (receivedBytes > maxBytes) {
          await reader.cancel();
          return {
            ok: false,
            response: jsonError('request body too large', 413),
          };
        }
        rawBody += decoder.decode(value, { stream: true });
      }
      rawBody += decoder.decode();
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
