import { relativeTarget, targetPath } from './paths.mjs';

export function uninstallTarget(id, label, relativePath, scope, options = {}) {
  const path = targetPath(relativePath);
  return {
    id,
    label,
    path,
    relative_path: relativeTarget(path),
    scope,
    mutates: true,
    selected: false,
    reason: options.reason,
    blocking_files: (options.blockingFiles ?? []).map((blockingFile) => {
      const blockingPath = targetPath(blockingFile);
      return {
        path: blockingPath,
        relative_path: relativeTarget(blockingPath),
      };
    }),
  };
}

export function uninstallTargetGroup(id, label, relativePaths, scope) {
  const paths = relativePaths.map((relativePath) => targetPath(relativePath));
  return {
    id,
    label,
    path: null,
    relative_path: `${relativePaths.length} discovered ${label.toLowerCase()}`,
    paths,
    relative_paths: paths.map((path) => relativeTarget(path)),
    scope,
    mutates: true,
    selected: false,
    blocking_files: [],
  };
}
