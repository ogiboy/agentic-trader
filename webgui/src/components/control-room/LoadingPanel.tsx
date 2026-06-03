import { useTranslations } from 'next-intl';

export function ControlRoomLoadingPanel({
  loadingSeconds,
}: Readonly<{
  loadingSeconds: number;
}>) {
  const t = useTranslations('controlRoom.shell');

  return (
    <div className='loading loading--panel' role='status' aria-live='polite'>
      <div className='loading__title'>{t('loading')}</div>
      <div className='loading__detail'>{t('loadingDetail')}</div>
      {loadingSeconds > 1 ? (
        <div className='loading__elapsed'>
          {t('loadingElapsed', { seconds: loadingSeconds })}
        </div>
      ) : null}
    </div>
  );
}

export function ControlRoomUnavailablePanel() {
  const t = useTranslations('controlRoom.shell');

  return <div className='loading'>{t('unavailable')}</div>;
}
