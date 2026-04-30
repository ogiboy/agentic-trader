export type JsonObjectBodyResult =
  | { ok: true; body: Record<string, unknown> }
  | { ok: false; response: Response };

export async function parseJsonObjectBody(
  request: Request,
): Promise<JsonObjectBodyResult> {
  try {
    const parsed: unknown = await request.json();
    if (
      typeof parsed !== 'object' ||
      parsed === null ||
      Array.isArray(parsed)
    ) {
      return {
        ok: false,
        response: Response.json({ error: 'invalid json' }, { status: 400 }),
      };
    }
    return { ok: true, body: parsed as Record<string, unknown> };
  } catch {
    return {
      ok: false,
      response: Response.json({ error: 'invalid json' }, { status: 400 }),
    };
  }
}
