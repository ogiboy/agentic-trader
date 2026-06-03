import React from 'react';
import { ChatPage } from './pages/chat-page.mjs';
import { MemoryPage } from './pages/memory-page.mjs';
import { OverviewPage } from './pages/overview-page.mjs';
import { PortfolioPage } from './pages/portfolio-page.mjs';
import { ReviewPage } from './pages/review-page.mjs';
import { RuntimePage } from './pages/runtime-page.mjs';
import { SettingsPage } from './pages/settings-page.mjs';

const e = React.createElement;

/**
 * Return the UI component element for the given dashboard page key.
 *
 * @param {Object} options - View selection and page state.
 * @param {string} options.page - Page key: 'overview', 'runtime', 'portfolio', 'review', 'memory', 'settings', or other (defaults to chat).
 * @param {Object} options.data - Dashboard snapshot and related data passed into the page component.
 * @param {{persona: string, history: Array<Object>, draft: string, busy: boolean}} options.chat - Chat page state.
 * @param {{draft: string, busy: boolean, mode: string, result: Object|null}} options.instruction - Settings page state.
 * @param {boolean} options.compact - Whether to render pages in compact mode (affects applicable pages).
 * @returns {import('react').ReactElement} The page element corresponding to `page`; unknown keys render the Chat page.
 */
function getPageView({ page, data, chat, instruction, compact }) {
  switch (page) {
    case 'overview':
      return e(OverviewPage, { data, compact });
    case 'runtime':
      return e(RuntimePage, { data });
    case 'portfolio':
      return e(PortfolioPage, { data });
    case 'review':
      return e(ReviewPage, { data });
    case 'memory':
      return e(MemoryPage, { data });
    case 'settings':
      return e(SettingsPage, {
        data,
        draft: instruction.draft,
        instructionBusy: instruction.busy,
        instructionMode: instruction.mode,
        instructionResult: instruction.result,
        compact,
      });
    default:
      return e(ChatPage, {
        data,
        persona: chat.persona,
        history: chat.history,
        draft: chat.draft,
        chatBusy: chat.busy,
      });
  }
}

export { getPageView };
