import { jsonError } from './responses';

export type JsonObjectBodyResult =
  | { ok: true; body: Record<string, unknown> }
  | { ok: false; response: Response };

type ParseJsonOptions = {
  maxBytes?: number;
};

const DEFAULT_MAX_JSON_BODY_BYTES = 32 * 1024;

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
