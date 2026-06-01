import {
  getPageForShortcut,
  rotateInstructionMode,
  rotatePersona,
} from './copy.mjs';

export function handleChatInput(input, key, handlers) {
  if (key.return) {
    handlers.sendChat();
    return true;
  }
  if (key.backspace || key.delete) {
    handlers.setChatDraft((current) => current.slice(0, -1));
    return true;
  }
  if (input === '[') {
    handlers.setChatPersona((current) => rotatePersona(current, -1));
    return true;
  }
  if (input === ']') {
    handlers.setChatPersona((current) => rotatePersona(current, 1));
    return true;
  }
  if (!key.ctrl && !key.meta && input) {
    handlers.setChatDraft((current) => current + input);
    return true;
  }
  return false;
}

export function handleSettingsInput(input, key, handlers) {
  if (key.return) {
    handlers.sendInstruction();
    return true;
  }
  if (key.backspace || key.delete) {
    handlers.setInstructionDraft((current) => current.slice(0, -1));
    return true;
  }
  if (input === '[') {
    handlers.setInstructionMode((current) =>
      rotateInstructionMode(current, -1),
    );
    return true;
  }
  if (input === ']') {
    handlers.setInstructionMode((current) => rotateInstructionMode(current, 1));
    return true;
  }
  if (!key.ctrl && !key.meta && input) {
    handlers.setInstructionDraft((current) => current + input);
    return true;
  }
  return false;
}

export function handleGlobalInput(input, handlers) {
  const normalized = input.toLowerCase();
  if (normalized === 'q') {
    handlers.exit();
    return true;
  }
  if (input === 'R') {
    handlers.runAction('restart');
    return true;
  }
  if (normalized === 'r') {
    handlers.refreshNow();
    return true;
  }
  if (normalized === 'o') {
    handlers.runAction('one-shot');
    return true;
  }
  if (normalized === 's') {
    handlers.runAction('start');
    return true;
  }
  if (normalized === 'x') {
    handlers.runAction('stop');
    return true;
  }
  const shortcutPage = getPageForShortcut(input);
  if (shortcutPage) {
    handlers.setPage(shortcutPage);
    return true;
  }
  return false;
}

export function handleDashboardInput(input, key, handlers) {
  if (key.rightArrow || input === '\t') {
    handlers.nextPage();
    return true;
  }
  if (key.leftArrow) {
    handlers.prevPage();
    return true;
  }
  const shortcutPage = getPageForShortcut(input);
  if (shortcutPage && !['chat', 'settings'].includes(handlers.page)) {
    handlers.setPage(shortcutPage);
    return true;
  }
  if (
    handlers.page === 'chat' &&
    handleChatInput(input, key, {
      sendChat: handlers.sendChat,
      setChatDraft: handlers.setChatDraft,
      setChatPersona: handlers.setChatPersona,
    })
  ) {
    return true;
  }
  if (
    handlers.page === 'settings' &&
    handleSettingsInput(input, key, {
      sendInstruction: handlers.sendInstruction,
      setInstructionDraft: handlers.setInstructionDraft,
      setInstructionMode: handlers.setInstructionMode,
    })
  ) {
    return true;
  }
  return handleGlobalInput(input, {
    exit: handlers.exit,
    refreshNow: handlers.refreshNow,
    runAction: handlers.runAction,
    setPage: handlers.setPage,
  });
}
