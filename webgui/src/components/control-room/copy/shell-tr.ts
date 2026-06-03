import type { ControlRoomCopy } from './types';

export const TR_SHELL_COPY = {
  actions: {
    oneShot: 'Tek Döngü',
    refresh: 'Yenile',
    restart: 'Yeniden Başlat',
    start: 'Başlat',
    stop: 'Durdur',
  },
  backend: 'Backend',
  eyebrow: 'Yerel-öncelikli kontrol odası',
  language: 'Dil',
  lastRefresh: 'Son yenileme',
  loading: 'Dashboard yükleniyor...',
  loadingDetail:
    'Yerel runtime, broker, model, araç ve research durumu toplanıyor. Yavaş provider kontrolleri birkaç saniye sürebilir.',
  loadingElapsed: (seconds) => `${seconds} sn bekleniyor`,
  mode: 'Mod',
  navAria: 'Bölümler',
  runtime: 'Çalışma',
  runtimeUnavailable: 'runtime kullanılamıyor',
  subtitle: 'Paper-first. Katı. Denetlenebilir.',
  title: 'Agentic Trader',
  unavailable: 'Dashboard kullanılamıyor.',
} satisfies ControlRoomCopy['shell'];

export const TR_TABS_COPY = {
  overview: 'Özet',
  runtime: 'Çalışma',
  portfolio: 'Portföy',
  proposals: 'Teklifler',
  review: 'İnceleme',
  memory: 'Karar Kanıtı',
  chat: 'Sohbet',
  settings: 'Ayarlar',
} satisfies ControlRoomCopy['tabs'];
