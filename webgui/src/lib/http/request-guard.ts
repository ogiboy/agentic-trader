import { jsonError } from './responses';

type RequestGuardOptions = {
  cooldownMs?: number;
  key: string;
  singleFlight?: boolean;
};

type RequestGuardResult =
  | { ok: true; release: () => void }
  | { ok: false; response: Response };

const inFlightRequests = new Set<string>();
const cooldownUntilByKey = new Map<string, number>();

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
