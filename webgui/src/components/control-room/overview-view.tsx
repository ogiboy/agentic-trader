import { Power, SlidersHorizontal, Wrench } from 'lucide-react';
import Image from 'next/image';

import type {
  DashboardData,
  KeyValueItems,
  ToolActionKind,
} from '../control-room.helpers';
import
  {
    asRecord,
    asRecordArray,
    asString,
    formatTimestamp,
    localToolActionLines,
    localToolLines,
    marketLensImage,
    providerWarningLines,
    readinessLines,
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
  const agentActivity = asRecord(dashboard.agentActivity);
  const status = asRecord(dashboard.status);
  const broker = asRecord(dashboard.broker);
  const calendar = asRecord(dashboard.calendar);
  const session = asRecord(calendar.session);
  const doctor = asRecord(dashboard.doctor);
  const camofoxService = asRecord(dashboard.camofoxService);
  const recentStageEvents = asRecordArray(agentActivity.recent_stage_events)
    .length
    ? asRecordArray(agentActivity.recent_stage_events).map(
        (event) =>
          `${formatTimestamp(event.created_at)} | ${asString(event.stage)} | ${asString(event.status)} | ${asString(event.message)}`,
      )
    : [copy.overview.emptyStageEvents];
  const localToolActions = localToolActionLines(dashboard, copy);
  const canStartCamofoxService =
    camofoxService.access_key_configured === true;

  return (
    <div className='stack'>
      <section className='market-ribbon'>
        <Image
          className='market-ribbon__image'
          src={marketLensImage}
          alt={copy.hero.alt}
          fill
          priority
          sizes='(max-width: 960px) 100vw, 50vw'
        />
        <div className='market-ribbon__overlay'>
          <div>
            <p className='eyebrow'>{copy.hero.eyebrow}</p>
            <h1>{copy.hero.title}</h1>
            <p className='market-ribbon__copy'>{copy.hero.copy}</p>
          </div>
          <div className='pill-row'>
            <span className='pill'>{asString(status.runtime_mode)}</span>
            <span className='pill'>{asString(broker.backend)}</span>
            <span className='pill'>
              {asString(session.venue, copy.hero.sessionUnknown)}
            </span>
            <span className='pill'>{asString(doctor.model)}</span>
          </div>
        </div>
      </section>

      <div className='grid grid--2'>
        <Panel title={copy.overview.panels.currentCycle} accent='lime'>
          <KeyValueList items={currentCycle} />
        </Panel>
        <Panel title={copy.overview.panels.system} accent='cyan'>
          <KeyValueList items={system} />
        </Panel>
      </div>

      <div className='grid grid--2'>
        <Panel title={copy.overview.panels.readinessGates} accent='rose'>
          <TextList items={readinessLines(dashboard, copy)} />
        </Panel>
        <Panel title={copy.overview.panels.localTools} accent='cyan'>
          <div className='tool-actions'>
            <button
              className='button'
              disabled={busy !== null}
              onClick={() => onToolAction('enable-local-tools')}
              type='button'
            >
              <SlidersHorizontal aria-hidden='true' size={16} />
              {copy.overview.tools.appTools}
            </button>
            <button
              className='button'
              disabled={busy !== null}
              onClick={() => onToolAction('enable-host-fallbacks')}
              type='button'
            >
              <SlidersHorizontal aria-hidden='true' size={16} />
              {copy.overview.tools.hostFallback}
            </button>
            <button
              className='button'
              disabled={busy !== null}
              onClick={() => onToolAction('start-model-service')}
              type='button'
            >
              <Power aria-hidden='true' size={16} />
              {copy.overview.tools.ollama}
            </button>
            <button
              className='button'
              disabled={busy !== null || !canStartCamofoxService}
              onClick={() => onToolAction('start-camofox-service')}
              type='button'
            >
              <Wrench aria-hidden='true' size={16} />
              {copy.overview.tools.camofox}
            </button>
          </div>
          {localToolActions.length ? (
            <div className='banner banner--warn'>
              <TextList items={localToolActions} />
            </div>
          ) : null}
          <TextList items={localToolLines(dashboard, copy)} />
        </Panel>
      </div>

      <Panel title={copy.overview.panels.providerWarnings} accent='amber'>
        <TextList items={providerWarningLines(dashboard, copy)} />
      </Panel>

      <Panel title={copy.overview.panels.decisionWorkflow} accent='amber'>
        <TextList items={recentStageEvents} />
      </Panel>
    </div>
  );
}
