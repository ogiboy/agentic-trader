import type { JsonRecord } from '@/lib/json-record';

export type DashboardRecord = JsonRecord;
export type DashboardData = DashboardRecord;
export type InstructionResult = DashboardRecord;

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
