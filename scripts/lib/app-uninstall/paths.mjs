import { existsSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const DEFAULT_ROOT_DIR = join(
  dirname(fileURLToPath(import.meta.url)),
  '..',
  '..',
  '..',
);

export const ROOT_DIR = resolve(
  process.env.AGENTIC_TRADER_APP_UNINSTALL_ROOT ?? DEFAULT_ROOT_DIR,
);

export function rootLooksLikeAgenticTrader(rootDir) {
  return (
    existsSync(join(rootDir, 'package.json')) &&
    existsSync(join(rootDir, 'pyproject.toml'))
  );
}

export function assertSafeRoot(rootDir) {
  if (!rootLooksLikeAgenticTrader(rootDir)) {
    process.stderr.write(
      `Refusing to uninstall from ${rootDir}: expected package.json and pyproject.toml markers.\n`,
    );
    process.exit(2);
  }
}

export function relativeTarget(path) {
  const rel = relative(ROOT_DIR, path);
  return rel === '' ? '.' : rel;
}

export function targetPath(relativePath) {
  const resolvedPath = resolve(ROOT_DIR, relativePath);
  const rootWithSep = ROOT_DIR.endsWith(sep) ? ROOT_DIR : `${ROOT_DIR}${sep}`;
  if (resolvedPath !== ROOT_DIR && !resolvedPath.startsWith(rootWithSep)) {
    throw new Error(
      `Refusing to target path outside app root: ${relativePath}`,
    );
  }
  return resolvedPath;
}
