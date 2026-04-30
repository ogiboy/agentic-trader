import type { ComponentProps } from 'react';

export type HomeBadge = {
  label: string;
  variant: ComponentProps<'span'>['className'] extends never
    ? never
    : 'secondary' | 'outline';
};

export type HomeEntryPoint = {
  href: `/${string}`;
  title: string;
  description: string;
  badge: string;
};

export type WorkflowTrack = {
  id: string;
  label: string;
  cards: {
    title: string;
    body: string;
  }[];
};

export type HomeContent = {
  badges: HomeBadge[];
  heroTitle: string;
  heroDescription: string;
  primaryAction: string;
  secondaryAction: {
    href: `/${string}`;
    label: string;
  };
  trustCards: {
    runtime: { title: string; body: string };
    safety: { title: string; body: string };
    surface: { title: string; body: string };
  };
  currentFocusItems: {
    icon: 'bot' | 'layout' | 'inspect';
    text: string;
  }[];
  guardrail: string;
  entryPoints: HomeEntryPoint[];
  workflowTracks: WorkflowTrack[];
};
