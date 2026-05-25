import type { ReactNode, SyntheticEvent } from 'react';

import type {
  DashboardData,
  MessageTone,
  TabId,
} from '../control-room.helpers';
import { cx, localizedStatusText } from '../control-room.helpers';
import {
  CONTROL_ROOM_LOCALES,
  normalizeControlRoomLocale,
  type ControlRoomCopy,
  type ControlRoomLocale,
} from './labels';
import { WebguiTokenPrompt } from './primitives';

export type RuntimeActionKind =
  | 'refresh'
  | 'start'
  | 'stop'
  | 'restart'
  | 'one-shot';

export type ControlRoomMessage = {
  text: string;
  tone: MessageTone;
};

type LocalizedTab = {
  id: TabId;
  label: string;
};

type ControlRoomAuthShellProps = {
  authBusy: boolean;
  authError: string | null;
  copy: ControlRoomCopy;
  onSubmit: (event: SyntheticEvent<HTMLFormElement>) => void;
  onTokenChange: (value: string) => void;
  token: string;
};

export function ControlRoomAuthShell({
  authBusy,
  authError,
  copy,
  onSubmit,
  onTokenChange,
  token,
}: Readonly<ControlRoomAuthShellProps>) {
  return (
    <div className='auth-shell'>
      <WebguiTokenPrompt
        busy={authBusy}
        copy={copy.auth}
        error={authError}
        onSubmit={onSubmit}
        onTokenChange={onTokenChange}
        token={token}
      />
    </div>
  );
}

type ControlRoomShellProps = {
  activeTabLabel: string;
  busy: string | null;
  content: ReactNode;
  copy: ControlRoomCopy;
  dashboard: DashboardData | null;
  error: string | null;
  lastLoadedAt: string;
  locale: ControlRoomLocale;
  message: ControlRoomMessage | null;
  tabs: LocalizedTab[];
  tab: TabId;
  onRunAction: (kind: RuntimeActionKind) => void;
  onSelectLocale: (locale: ControlRoomLocale) => void;
  onSelectTab: (tab: TabId) => void;
};

export function ControlRoomShell({
  activeTabLabel,
  busy,
  content,
  copy,
  dashboard,
  error,
  lastLoadedAt,
  locale,
  message,
  tabs,
  tab,
  onRunAction,
  onSelectLocale,
  onSelectTab,
}: Readonly<ControlRoomShellProps>) {
  return (
    <div className='shell'>
      <aside className='sidebar'>
        <div className='sidebar__brand'>
          <div className='sidebar__eyebrow'>{copy.shell.eyebrow}</div>
          <div className='sidebar__title'>{copy.shell.title}</div>
          <div className='sidebar__subtitle'>{copy.shell.subtitle}</div>
        </div>

        <nav className='sidebar__nav' aria-label={copy.shell.navAria}>
          {tabs.map((item) => (
            <button
              className={cx(
                'nav-button',
                item.id === tab && 'nav-button--active',
              )}
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              type='button'
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className='sidebar__meta'>
          <label className='field-label'>
            <span>{copy.shell.language}</span>
            <select
              value={locale}
              onChange={(event) =>
                onSelectLocale(normalizeControlRoomLocale(event.target.value))
              }
            >
              {CONTROL_ROOM_LOCALES.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <div>
            {copy.shell.runtime}: {dashboard?.status?.runtime_state ?? '-'}
          </div>
          <div>
            {copy.shell.mode}:{' '}
            {dashboard?.status?.runtime_mode ??
              dashboard?.doctor?.runtime_mode ??
              '-'}
          </div>
          <div>
            {copy.shell.backend}: {dashboard?.broker?.backend ?? '-'}
          </div>
          <div>
            {copy.shell.lastRefresh}: {lastLoadedAt}
          </div>
        </div>
      </aside>

      <main className='main'>
        <header className='topbar'>
          <div className='topbar__status'>
            <span className='topbar__headline'>{activeTabLabel}</span>
            <span className='chip'>
              {dashboard?.status?.runtime_mode ??
                dashboard?.doctor?.runtime_mode ??
                '-'}
            </span>
            <span className='chip'>
              {dashboard?.broker?.execution_mode ?? '-'}
            </span>
            <span className='chip chip--message'>
              {localizedStatusText(
                dashboard?.broker?.message ?? copy.shell.runtimeUnavailable,
                copy,
              )}
            </span>
          </div>
          <div className='topbar__actions'>
            <button
              className='button'
              disabled={busy !== null}
              onClick={() => onRunAction('refresh')}
              type='button'
            >
              {copy.shell.actions.refresh}
            </button>
            <button
              className='button'
              disabled={busy !== null}
              onClick={() => onRunAction('one-shot')}
              type='button'
            >
              {copy.shell.actions.oneShot}
            </button>
            <button
              className='button'
              disabled={busy !== null}
              onClick={() => onRunAction('start')}
              type='button'
            >
              {copy.shell.actions.start}
            </button>
            <button
              className='button'
              disabled={busy !== null}
              onClick={() => onRunAction('stop')}
              type='button'
            >
              {copy.shell.actions.stop}
            </button>
            <button
              className='button'
              disabled={busy !== null}
              onClick={() => onRunAction('restart')}
              type='button'
            >
              {copy.shell.actions.restart}
            </button>
          </div>
        </header>

        {message ? (
          <div
            aria-live='polite'
            className={cx('banner', `banner--${message.tone}`)}
            role='status'
          >
            {message.text}
          </div>
        ) : null}
        {error ? <div className='banner banner--bad'>{error}</div> : null}

        {content}
      </main>
    </div>
  );
}
