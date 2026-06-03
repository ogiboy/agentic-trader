import { EN_CONTROL_ROOM_COPY } from '@/components/control-room/copy/en';
import { TR_CONTROL_ROOM_COPY } from '@/components/control-room/copy/tr';
import type { ControlRoomCopy } from '@/components/control-room/copy/types';

import type { WebguiLocale } from './locales';

const SHELL_LOADING_ELAPSED: Record<WebguiLocale, string> = {
  en: 'Waiting {seconds}s',
  tr: '{seconds} sn bekleniyor',
};

const PROPOSAL_STOP_TAKE: Record<WebguiLocale, string> = {
  en: 'stop {stop} / take {take}',
  tr: 'stop {stop} / take {take}',
};

const OLLAMA_MODEL_MISSING: Record<WebguiLocale, string> = {
  en: 'Ollama is reachable but {model} is not available yet.',
  tr: 'Ollama erişilebilir ama {model} henüz yok.',
};

function controlRoomMessages(copy: ControlRoomCopy, locale: WebguiLocale) {
  const { diagnostics, proposals, settings, shell, ...rest } = copy;
  const diagnosticsMessages = {
    ...diagnostics,
    actions: {
      ...diagnostics.actions,
      ollamaModelMissing: OLLAMA_MODEL_MISSING[locale],
    },
  };
  const proposalMessages: Omit<ControlRoomCopy['proposals'], 'stopTake'> = {
    actions: proposals.actions,
    fields: proposals.fields,
    notePlaceholder: proposals.notePlaceholder,
    panels: proposals.panels,
  };
  const settingsMessages: Omit<ControlRoomCopy['settings'], 'examples'> = {
    actions: settings.actions,
    fields: settings.fields,
    instructionEmpty: settings.instructionEmpty,
    modeOptions: settings.modeOptions,
    panels: settings.panels,
    placeholder: settings.placeholder,
    recentRunsEmpty: settings.recentRunsEmpty,
  };
  const shellMessages: Omit<ControlRoomCopy['shell'], 'loadingElapsed'> = {
    actions: shell.actions,
    backend: shell.backend,
    eyebrow: shell.eyebrow,
    language: shell.language,
    lastRefresh: shell.lastRefresh,
    loading: shell.loading,
    loadingDetail: shell.loadingDetail,
    mode: shell.mode,
    navAria: shell.navAria,
    runtime: shell.runtime,
    runtimeUnavailable: shell.runtimeUnavailable,
    subtitle: shell.subtitle,
    title: shell.title,
    unavailable: shell.unavailable,
  };

  return {
    controlRoom: {
      ...rest,
      diagnostics: diagnosticsMessages,
      proposals: {
        ...proposalMessages,
        stopTake: PROPOSAL_STOP_TAKE[locale],
      },
      settings: {
        ...settingsMessages,
        examples: {
          conservative: settings.examples[0] ?? '',
          capitalPreservation: settings.examples[1] ?? '',
        },
      },
      shell: {
        ...shellMessages,
        loadingElapsed: SHELL_LOADING_ELAPSED[locale],
      },
    },
  } as const;
}

export const EN_MESSAGES = controlRoomMessages(EN_CONTROL_ROOM_COPY, 'en');
export const TR_MESSAGES = controlRoomMessages(TR_CONTROL_ROOM_COPY, 'tr');

export const WEBGUI_MESSAGES = {
  en: EN_MESSAGES,
  tr: TR_MESSAGES,
} as const;

export type WebguiMessages = typeof EN_MESSAGES;
