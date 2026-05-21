export class WebguiHttpError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'WebguiHttpError';
    this.status = status;
  }
}

export type DashboardRequestContext = {
  controller: AbortController;
  seq: number;
};

/**
 * Checks whether a dashboard request corresponds to the current active request.
 *
 * @param request - The in-flight dashboard request context containing an AbortController and sequence number.
 * @param latestSeq - The most recent request sequence number to compare against.
 * @returns True when the request has not been aborted and still matches the latest sequence.
 */
export function isDashboardRequestCurrent(
  request: DashboardRequestContext,
  latestSeq: number,
): boolean {
  return !request.controller.signal.aborted && request.seq === latestSeq;
}

/**
 * Convert an unknown error value into a human-readable message.
 *
 * @param error - The error value to format.
 * @returns The error message when available, otherwise the stringified value.
 */
export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/**
 * Fetches JSON from the given URL and returns the parsed payload.
 *
 * @param url - The endpoint URL to fetch.
 * @param init - Optional fetch init options; headers are merged with the default JSON header.
 * @returns The parsed JSON payload cast to `T`.
 * @throws WebguiHttpError when the response has a non-OK status.
 */
export async function readJson<T>(url: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  const requestInit: RequestInit = {};
  if (init) {
    Object.assign(requestInit, init);
    delete requestInit.headers;
  }

  const response = await fetch(url, {
    ...requestInit,
    headers,
    cache: 'no-store',
    credentials: 'same-origin',
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new WebguiHttpError(
      payload.error || 'Request failed.',
      response.status,
    );
  }
  return payload as T;
}

export async function authenticateWebguiSession(token: string): Promise<void> {
  await readJson<{ authenticated: boolean; tokenRequired: boolean }>(
    '/api/session',
    {
      method: 'POST',
      body: JSON.stringify({ token }),
    },
  );
}
