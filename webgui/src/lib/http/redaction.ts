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
const PYTHON_EXCEPTION_PATTERN =
  /\b[A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception):\s+\S[\s\S]*$/;

function escapeRegExp(value: string): string {
  return value.replaceAll(/[.*+?^${}()|[\]\\]/g, String.raw`\$&`);
}

function compactTraceback(value: string): string {
  if (!value.includes('Traceback (most recent call last)')) {
    return value;
  }
  const match = PYTHON_EXCEPTION_PATTERN.exec(value);
  if (match?.[0]) {
    return match[0].replaceAll(/\s+/g, ' ').trim();
  }
  return 'Agentic Trader command failed. Check local runtime logs for details.';
}

function sensitiveEnvValues(): string[] {
  return Object.entries(process.env)
    .filter(
      ([key, value]) => SECRET_ENV_NAME_PATTERN.test(key) && Boolean(value),
    )
    .map(([, value]) => String(value))
    .filter((value) => value.length >= 4)
    .sort((left, right) => right.length - left.length);
}

export function redactAndCapText(value: unknown, maxLength = 2_000): string {
  let text = compactTraceback(
    value instanceof Error ? value.message : String(value),
  );
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
