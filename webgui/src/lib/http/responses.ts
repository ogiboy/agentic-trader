export function jsonError(
  error: string,
  status: number,
  headers?: HeadersInit,
): Response {
  return Response.json({ error }, { status, headers });
}
