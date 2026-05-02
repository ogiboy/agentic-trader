import type { HomeContent } from '@/lib/home/content/types';

export const homeContentEn: HomeContent = {
  badges: [
    { label: 'Developer Docs', variant: 'secondary' },
    { label: 'Fumadocs + MDX', variant: 'outline' },
    { label: 'Local-first', variant: 'outline' },
  ],
  heroTitle: 'Build from the same runtime truth the operator sees.',
  heroDescription:
    'Agentic Trader is not a second-order chat demo. These docs are the developer surface for a strict, paper-first trading runtime with inspectable storage, explicit safety gates, and shared contracts across CLI, Ink, observer API, and Web GUI.',
  primaryAction: 'Read the docs',
  secondaryAction: {
    href: '/docs/getting-started',
    label: 'Open quick start',
  },
  trustCards: {
    runtime: {
      title: 'Runtime-first',
      body: 'Model service, runtime state, broker state, and review surfaces should agree before we trust a cycle.',
    },
    safety: {
      title: 'Guardrailed',
      body: 'Paper execution, strict LLM gating, provider visibility, and no silent runtime fallbacks remain non-negotiable.',
    },
    surface: {
      title: 'Multi-surface',
      body: 'CLI, Rich, Ink, observer API, and Web GUI all ride the same contracts instead of maintaining UI-only truth.',
    },
  },
  currentFocusItems: [
    {
      icon: 'bot',
      text: 'Optional app-managed Ollama supervision should extend the existing daemon and log surface.',
    },
    {
      icon: 'layout',
      text: '`webgui` stays a thin local shell while `docs` becomes the canonical dev-docs surface.',
    },
    {
      icon: 'inspect',
      text: 'Bootstrap, provider readiness, and QA evidence are all moving toward a more standardized onboarding path.',
    },
  ],
  guardrail:
    'The Web GUI and docs site are developer/operator surfaces. They do not own orchestration; Python runtime contracts remain the source of truth.',
  entryPoints: [
    {
      href: '/docs/getting-started',
      title: 'Get Started',
      description:
        'Install the repo, run doctor, validate model readiness, and open the main operator surfaces.',
      badge: 'Setup',
    },
    {
      href: '/docs/architecture',
      title: 'Architecture',
      description:
        'Read package ownership, runtime boundaries, and why the repo refuses a parallel orchestration layer.',
      badge: 'System map',
    },
    {
      href: '/docs/runtime-and-operations',
      title: 'Runtime And Operations',
      description:
        'Understand modes, supervision, logs, stop controls, and operator-visible runtime truth.',
      badge: 'Operations',
    },
    {
      href: '/docs/data-and-intelligence',
      title: 'Data And Intelligence',
      description:
        'See how market context, provider normalization, and feature bundles feed the agent graph.',
      badge: 'Signals',
    },
    {
      href: '/docs/frontend-system',
      title: 'Frontend System',
      description:
        'Keep `docs` and `webgui` aligned on the shared shadcn preset, local-first monospace typography, and modular file organization.',
      badge: 'Frontend',
    },
    {
      href: '/docs/memory-and-review',
      title: 'Memory And Review',
      description:
        'See how docs, `.ai` notes, feedback drafts, and review artifacts stay aligned with runtime reality.',
      badge: 'Continuity',
    },
    {
      href: '/docs/qa-and-debugging',
      title: 'QA And Debugging',
      description:
        'Use smoke QA, runtime evidence, and operator-truth checks before treating a change as shippable.',
      badge: 'Validation',
    },
  ],
  workflowTracks: [
    {
      id: 'build',
      label: 'Build',
      cards: [
        {
          title: 'Setup track',
          body: 'Start with `README.md`, then validate the environment with `doctor`, local model readiness, and the docs quick start.',
        },
        {
          title: 'Architecture track',
          body: 'Use `dev/code-map.md` plus the architecture docs to find the smallest owning module before editing.',
        },
        {
          title: 'Frontend track',
          body: '`webgui` and `docs` share Next.js App Router, Tailwind v4, and shadcn primitives, but they should not invent a shared package prematurely.',
        },
      ],
    },
    {
      id: 'operate',
      label: 'Operate',
      cards: [
        {
          title: 'Runtime mode',
          body: 'Operation and training are runtime overlays with different safety expectations, not two separate products.',
        },
        {
          title: 'Operator surfaces',
          body: 'CLI, Ink, Rich, observer API, and Web GUI should all describe the same daemon, broker, and review state.',
        },
        {
          title: 'Feedback flow',
          body: 'Pages docs feedback prepares a browser-local GitHub issue draft; server-side forwarding should only occur when the docs site is explicitly hosted on a Node server.',
        },
      ],
    },
    {
      id: 'inspect',
      label: 'Inspect',
      cards: [
        {
          title: 'Review track',
          body: 'Use trace, review, trade context, and memory inspection before treating an agent answer as sufficient evidence.',
        },
        {
          title: 'Quality track',
          body: 'Treat Ruff, Pytest, Pyright, smoke QA, and UI checks as a layered quality system instead of a single green check.',
        },
        {
          title: 'Docs track',
          body: 'Whenever runtime behavior or assumptions move, update `.ai/current-state.md`, `.ai/tasks.md`, `.ai/decisions.md`, and the matching docs page together.',
        },
      ],
    },
  ],
};
