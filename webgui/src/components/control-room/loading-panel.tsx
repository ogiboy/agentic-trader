import type { ControlRoomCopy } from './labels';

export function ControlRoomLoadingPanel({
  copy,
  loadingSeconds,
}: Readonly<{
  copy: ControlRoomCopy;
  loadingSeconds: number;
}>) {
  return (
    <div className='loading loading--panel' role='status' aria-live='polite'>
      <div className='loading__title'>{copy.shell.loading}</div>
      <div className='loading__detail'>{copy.shell.loadingDetail}</div>
      {loadingSeconds > 1 ? (
        <div className='loading__elapsed'>
          {copy.shell.loadingElapsed(loadingSeconds)}
        </div>
      ) : null}
    </div>
  );
}

export function ControlRoomUnavailablePanel({
  copy,
}: Readonly<{
  copy: ControlRoomCopy;
}>) {
  return <div className='loading'>{copy.shell.unavailable}</div>;
}
