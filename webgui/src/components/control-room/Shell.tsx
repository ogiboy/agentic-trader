import type { ReactNode, SyntheticEvent } from 'react';
import { useTranslations } from 'next-intl';

import type {
  DashboardData,
  MessageTone,
  TabId,
} from '../control-room.helpers';
import
  {
    asRecord,
    asString,
    cx,
    localizedStatusText,
    type ControlRoomDiagnosticsCopySource,
  } from '../control-room.helpers';
import {
  WEBGUI_LOCALE_OPTIONS,
  normalizeWebguiLocale,
  type WebguiLocale,
} from '@/i18n/locales';
import { WebguiTokenPrompt } from './Primitives';

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
  onSubmit: (event: SyntheticEvent<HTMLFormElement>) => void;
  onTokenChange: (value: string) => void;
  token: string;
};

export function ControlRoomAuthShell({
  authBusy,
  authError,
  onSubmit,
  onTokenChange,
  token,
}: Readonly<ControlRoomAuthShellProps>) {
  const t = useTranslations('controlRoom.auth');

  return (
    <div className='auth-shell'>
      <WebguiTokenPrompt
        busy={authBusy}
        copy={{
          body: t('body'),
          eyebrow: t('eyebrow'),
          title: t('title'),
          tokenLabel: t('tokenLabel'),
          unlock: t('unlock'),
          unlocking: t('unlocking'),
        }}
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
  dashboard: DashboardData | null;
  diagnosticsCopy: ControlRoomDiagnosticsCopySource;
  error: string | null;
  lastLoadedAt: string;
  locale: WebguiLocale;
  message: ControlRoomMessage | null;
  tabs: LocalizedTab[];
  tab: TabId;
  onRunAction: (kind: RuntimeActionKind) => void;
  onSelectLocale: (locale: WebguiLocale) => void;
  onSelectTab: (tab: TabId) => void;
};

export function ControlRoomShell({
  activeTabLabel,
  busy,
  content,
  dashboard,
  diagnosticsCopy,
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
  const t = useTranslations('controlRoom.shell');
  const status = asRecord(dashboard?.status);
  const doctor = asRecord(dashboard?.doctor);
  const broker = asRecord(dashboard?.broker);
  const runtimeMode = asString(
    status.runtime_mode,
    asString(doctor.runtime_mode),
  );

  return (
    <div className='shell'>
      <aside className='sidebar'>
        <div className='sidebar__brand'>
          <div className='sidebar__eyebrow'>{t('eyebrow')}</div>
          <div className='sidebar__title'>{t('title')}</div>
          <div className='sidebar__subtitle'>{t('subtitle')}</div>
        </div>

        <nav className='sidebar__nav' aria-label={t('navAria')}>
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
            <span>{t('language')}</span>
            <select
              value={locale}
              onChange={(event) =>
                onSelectLocale(normalizeWebguiLocale(event.target.value))
              }
            >
              {WEBGUI_LOCALE_OPTIONS.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <div>
            {t('runtime')}: {asString(status.runtime_state)}
          </div>
          <div>
            {t('mode')}: {runtimeMode}
          </div>
          <div>
            {t('backend')}: {asString(broker.backend)}
          </div>
          <div>
            {t('lastRefresh')}: {lastLoadedAt}
          </div>
        </div>
      </aside>

      <main className='main'>
        <header className='topbar'>
          <div className='topbar__status'>
            <span className='topbar__headline'>{activeTabLabel}</span>
            <span className='chip'>{runtimeMode}</span>
            <span className='chip'>{asString(broker.execution_mode)}</span>
            <span className='chip chip--message'>
              {localizedStatusText(
                asString(broker.message, t('runtimeUnavailable')),
                diagnosticsCopy,
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
              {t('actions.refresh')}
            </button>
            <button
              className='button'
              disabled={busy !== null}
              onClick={() => onRunAction('one-shot')}
              type='button'
            >
              {t('actions.oneShot')}
            </button>
            <button
              className='button'
              disabled={busy !== null}
              onClick={() => onRunAction('start')}
              type='button'
            >
              {t('actions.start')}
            </button>
            <button
              className='button'
              disabled={busy !== null}
              onClick={() => onRunAction('stop')}
              type='button'
            >
              {t('actions.stop')}
            </button>
            <button
              className='button'
              disabled={busy !== null}
              onClick={() => onRunAction('restart')}
              type='button'
            >
              {t('actions.restart')}
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
