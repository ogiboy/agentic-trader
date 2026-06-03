import { Power, SlidersHorizontal, Wrench } from 'lucide-react';
import Image from 'next/image';
import { useTranslations } from 'next-intl';

import {
  asRecord,
  asRecordArray,
  asString,
  formatTimestamp,
  localToolActionLines,
  localToolLines,
  marketLensImage,
  providerWarningLines,
  readinessLines,
  type ControlRoomDiagnosticsCopySource,
  type DashboardData,
  type KeyValueItems,
  type ToolActionKind,
} from '../control-room.helpers';
import { KeyValueList, Panel, TextList } from './Primitives';

export function OverviewView({
  dashboard,
  diagnosticsCopy,
  currentCycle,
  system,
  busy,
  onToolAction,
}: Readonly<{
  dashboard: DashboardData;
  diagnosticsCopy: ControlRoomDiagnosticsCopySource;
  currentCycle: KeyValueItems;
  system: KeyValueItems;
  busy: string | null;
  onToolAction: (kind: ToolActionKind) => void;
}>) {
  const hero = useTranslations('controlRoom.hero');
  const overview = useTranslations('controlRoom.overview');
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
    : [overview('emptyStageEvents')];
  const localToolActions = localToolActionLines(dashboard, diagnosticsCopy);
  const canStartCamofoxService =
    camofoxService.access_key_configured === true;

  return (
    <div className='stack'>
      <section className='market-ribbon'>
        <Image
          className='market-ribbon__image'
          src={marketLensImage}
          alt={hero('alt')}
          fill
          priority
          sizes='(max-width: 960px) 100vw, 50vw'
        />
        <div className='market-ribbon__overlay'>
          <div>
            <p className='eyebrow'>{hero('eyebrow')}</p>
            <h1>{hero('title')}</h1>
            <p className='market-ribbon__copy'>{hero('copy')}</p>
          </div>
          <div className='pill-row'>
            <span className='pill'>{asString(status.runtime_mode)}</span>
            <span className='pill'>{asString(broker.backend)}</span>
            <span className='pill'>
              {asString(session.venue, hero('sessionUnknown'))}
            </span>
            <span className='pill'>{asString(doctor.model)}</span>
          </div>
        </div>
      </section>

      <div className='grid grid--2'>
        <Panel title={overview('panels.currentCycle')} accent='lime'>
          <KeyValueList items={currentCycle} />
        </Panel>
        <Panel title={overview('panels.system')} accent='cyan'>
          <KeyValueList items={system} />
        </Panel>
      </div>

      <div className='grid grid--2'>
        <Panel title={overview('panels.readinessGates')} accent='rose'>
          <TextList items={readinessLines(dashboard, diagnosticsCopy)} />
        </Panel>
        <Panel title={overview('panels.localTools')} accent='cyan'>
          <div className='tool-actions'>
            <button
              className='button'
              disabled={busy !== null}
              onClick={() => onToolAction('enable-local-tools')}
              type='button'
            >
              <SlidersHorizontal aria-hidden='true' size={16} />
              {overview('tools.appTools')}
            </button>
            <button
              className='button'
              disabled={busy !== null}
              onClick={() => onToolAction('enable-host-fallbacks')}
              type='button'
            >
              <SlidersHorizontal aria-hidden='true' size={16} />
              {overview('tools.hostFallback')}
            </button>
            <button
              className='button'
              disabled={busy !== null}
              onClick={() => onToolAction('start-model-service')}
              type='button'
            >
              <Power aria-hidden='true' size={16} />
              {overview('tools.ollama')}
            </button>
            <button
              className='button'
              disabled={busy !== null || !canStartCamofoxService}
              onClick={() => onToolAction('start-camofox-service')}
              type='button'
            >
              <Wrench aria-hidden='true' size={16} />
              {overview('tools.camofox')}
            </button>
          </div>
          {localToolActions.length ? (
            <div className='banner banner--warn'>
              <TextList items={localToolActions} />
            </div>
          ) : null}
          <TextList items={localToolLines(dashboard, diagnosticsCopy)} />
        </Panel>
      </div>

      <Panel title={overview('panels.providerWarnings')} accent='amber'>
        <TextList items={providerWarningLines(dashboard, diagnosticsCopy)} />
      </Panel>

      <Panel title={overview('panels.decisionWorkflow')} accent='amber'>
        <TextList items={recentStageEvents} />
      </Panel>
    </div>
  );
}
