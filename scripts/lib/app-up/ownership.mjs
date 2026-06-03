function ownerDecision(tool, mode) {
  const notes = {
    undecided:
      'No ownership choice supplied yet; app:up will defer ownership-sensitive actions.',
    'host-owned':
      'Connect/readiness only; app:up must not start, stop, install, or delete this host-owned tool.',
    'app-owned':
      'App-owned setup/start may run only for explicitly selected scopes and records owner-only state through existing services.',
    'api-key-only':
      'Use ignored environment/keychain authentication only; no CLI install or service ownership is implied.',
    skipped:
      'Feature remains degraded/skipped while the paper-first product can still open.',
  };
  return {
    tool,
    mode,
    note: notes[mode],
  };
}

export function ownershipDecisions(options) {
  return [
    ownerDecision('ollama', options.owners.ollama),
    ownerDecision('firecrawl', options.owners.firecrawl),
    ownerDecision('camofox', options.owners.camofox),
  ];
}

export function ownershipUpdates(options) {
  return Object.fromEntries(
    [...options.ownerOverrides].map((tool) => [tool, options.owners[tool]]),
  );
}

export function ownerBlocker(step, owners) {
  if (!step.requires_owner) {
    return null;
  }
  const actual = owners[step.requires_owner.tool];
  if (actual === step.requires_owner.mode) {
    return null;
  }
  if (actual === 'undecided') {
    return `Choose --${step.requires_owner.tool}-owner=${step.requires_owner.mode} before selecting ${step.scope}.`;
  }
  return `${step.scope} requires ${step.requires_owner.tool} ownership ${step.requires_owner.mode}; current choice is ${actual}.`;
}
