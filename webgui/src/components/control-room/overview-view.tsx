/* eslint-disable @typescript-eslint/no-explicit-any -- dashboard payloads are schema-loose JSON today */
import Image from 'next/image';
import { Power, SlidersHorizontal, Wrench } from 'lucide-react';

import {
  formatTimestamp,
  localToolActionLines,
  localToolLines,
  marketLensImage,
  providerWarningLines,
  readinessLines,
} from '../control-room.helpers';
import type {
  DashboardData,
  KeyValueItems,
  ToolActionKind,
} from '../control-room.helpers';
import { getControlRoomCopy, type ControlRoomCopy } from './labels';
import { KeyValueList, Panel, TextList } from './primitives';

export function OverviewView({
  copy = getControlRoomCopy('en'),
  dashboard,
  currentCycle,
  system,
  busy,
  onToolAction,
}: Readonly<{
  copy?: ControlRoomCopy;
  dashboard: DashboardData;
  currentCycle: KeyValueItems;
  system: KeyValueItems;
  busy: string | null;
  onToolAction: (kind: ToolActionKind) => void;
}>) {
  const recentStageEvents = dashboard.agentActivity?.recent_stage_events?.length
    ? dashboard.agentActivity.recent_stage_events.map(
        (event: Record<string, any>) =>
          `${formatTimestamp(event.created_at)} | ${event.stage} | ${event.status} | ${event.message}`,
      )
    : [copy.overview.emptyStageEvents];
  const localToolActions = localToolActionLines(dashboard);
  const canStartCamofoxService =
    dashboard.camofoxService?.access_key_configured === true;

  return (
    <div className="stack">
      <section className="market-ribbon">
        <Image
          className="market-ribbon__image"
          src={marketLensImage}
          alt={copy.hero.alt}
          fill
          priority
          sizes="(max-width: 960px) 100vw, 50vw"
        />
        <div className="market-ribbon__overlay">
          <div>
            <p className="eyebrow">{copy.hero.eyebrow}</p>
            <h1>{copy.hero.title}</h1>
            <p className="market-ribbon__copy">{copy.hero.copy}</p>
          </div>
          <div className="pill-row">
            <span className="pill">
              {dashboard.status?.runtime_mode ?? '-'}
            </span>
            <span className="pill">{dashboard.broker?.backend ?? '-'}</span>
            <span className="pill">
              {dashboard.calendar?.session?.venue ?? copy.hero.sessionUnknown}
            </span>
            <span className="pill">{dashboard.doctor?.model ?? '-'}</span>
          </div>
        </div>
      </section>

      <div className="grid grid--2">
        <Panel title={copy.overview.panels.currentCycle} accent="lime">
          <KeyValueList items={currentCycle} />
        </Panel>
        <Panel title={copy.overview.panels.system} accent="cyan">
          <KeyValueList items={system} />
        </Panel>
      </div>

      <div className="grid grid--2">
        <Panel title={copy.overview.panels.readinessGates} accent="rose">
          <TextList items={readinessLines(dashboard)} />
        </Panel>
        <Panel title={copy.overview.panels.localTools} accent="cyan">
          <div className="tool-actions">
            <button
              className="button"
              disabled={busy !== null}
              onClick={() => onToolAction('enable-local-tools')}
              type="button"
            >
              <SlidersHorizontal aria-hidden="true" size={16} />
              {copy.overview.tools.appTools}
            </button>
            <button
              className="button"
              disabled={busy !== null}
              onClick={() => onToolAction('enable-host-fallbacks')}
              type="button"
            >
              <SlidersHorizontal aria-hidden="true" size={16} />
              {copy.overview.tools.hostFallback}
            </button>
            <button
              className="button"
              disabled={busy !== null}
              onClick={() => onToolAction('start-model-service')}
              type="button"
            >
              <Power aria-hidden="true" size={16} />
              {copy.overview.tools.ollama}
            </button>
            <button
              className="button"
              disabled={busy !== null || !canStartCamofoxService}
              onClick={() => onToolAction('start-camofox-service')}
              type="button"
            >
              <Wrench aria-hidden="true" size={16} />
              {copy.overview.tools.camofox}
            </button>
          </div>
          {localToolActions.length ? (
            <div className="banner banner--warn">
              <TextList items={localToolActions} />
            </div>
          ) : null}
          <TextList items={localToolLines(dashboard)} />
        </Panel>
      </div>

      <Panel title={copy.overview.panels.providerWarnings} accent="amber">
        <TextList items={providerWarningLines(dashboard)} />
      </Panel>

      <Panel title={copy.overview.panels.decisionWorkflow} accent="amber">
        <TextList items={recentStageEvents} />
      </Panel>
    </div>
  );
}
