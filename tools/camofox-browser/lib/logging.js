export function createJsonLogger({
  stderr = process.stderr,
  stdout = process.stdout,
} = {}) {
  return function log(level, msg, fields = {}) {
    const entry = {
      ts: new Date().toISOString(),
      level,
      msg,
      ...fields,
    };
    const line = JSON.stringify(entry);
    if (level === 'error') {
      stderr.write(line + '\n');
    } else {
      stdout.write(line + '\n');
    }
  };
}
