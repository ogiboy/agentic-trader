/* eslint-disable @typescript-eslint/no-explicit-any -- dashboard payloads are schema-loose JSON today */

export type DashboardData = Record<string, any>;

export type TabId =
  | 'overview'
  | 'runtime'
  | 'portfolio'
  | 'proposals'
  | 'review'
  | 'memory'
  | 'chat'
  | 'settings';

export type MessageTone = 'neutral' | 'good' | 'warn' | 'bad';
export type InstructionMode = 'preview' | 'apply';
export type PanelAccent = 'lime' | 'amber' | 'cyan' | 'rose';
export type KeyValueItems = Array<[string, string]>;

export type ToolActionKind =
  | 'enable-local-tools'
  | 'enable-host-fallbacks'
  | 'start-model-service'
  | 'start-camofox-service';

export type ProposalActionKind = 'approve' | 'reject' | 'reconcile' | 'refresh';
