import type { DocLanguage } from '@/lib/i18n/config';

export type FeedbackCopy = {
  title: string;
  description: string;
  helpful: string;
  needsWork: string;
  noteLabel: string;
  notePlaceholder: string;
  destinationSummary: string;
  submit: string;
  saving: string;
  successPrepared: string;
  successLocalOnlyDisabled: string;
  successLocalOnlyFailed: string;
  storageWarning: string;
  technicalDetail: string;
  openIssue: string;
  genericError: string;
};

const feedbackCopy: Record<DocLanguage, FeedbackCopy> = {
  en: {
    title: 'How was this page?',
    description:
      'This GitHub Pages build prepares a browser-local feedback draft and a prefilled GitHub issue. Node-hosted local docs can still wire feedback into runtime logs later.',
    helpful: 'Helpful',
    needsWork: 'Needs work',
    noteLabel: 'Optional note',
    notePlaceholder: 'Tell us what was clear, missing, or confusing.',
    destinationSummary:
      'Stores a draft in this browser and gives you a GitHub issue link to submit when ready.',
    submit: 'Prepare issue',
    saving: 'Preparing feedback...',
    successPrepared:
      'Feedback draft is ready. Open the prefilled GitHub issue to submit it.',
    successLocalOnlyDisabled:
      'Feedback draft was prepared locally in this browser.',
    successLocalOnlyFailed:
      'Feedback draft was prepared locally, but opening the external issue link failed.',
    storageWarning:
      'Browser local storage could not save the draft; the issue link is still ready.',
    technicalDetail: 'Technical detail',
    openIssue: 'Open GitHub issue',
    genericError: 'Failed to send feedback.',
  },
  tr: {
    title: 'Bu sayfa nasıl?',
    description:
      "Bu GitHub Pages build'i tarayıcı içinde yerel bir feedback taslağı ve hazır doldurulmuş GitHub issue bağlantısı üretir. Node-hosted local docs ileride runtime loglarına bağlanabilir.",
    helpful: 'İşe yaradı',
    needsWork: 'Geliştirilmeli',
    noteLabel: 'İsteğe bağlı not',
    notePlaceholder: 'Neyin açık, eksik veya kafa karıştırıcı olduğunu yaz.',
    destinationSummary:
      'Taslağı bu tarayıcıda tutar ve hazır olduğunda gönderebilmen için GitHub issue bağlantısı verir.',
    submit: 'Issue hazırla',
    saving: 'Geri bildirim hazırlanıyor...',
    successPrepared:
      'Geri bildirim taslağı hazır. Göndermek için hazır doldurulmuş GitHub issue bağlantısını aç.',
    successLocalOnlyDisabled:
      'Geri bildirim taslağı bu tarayıcıda yerel olarak hazırlandı.',
    successLocalOnlyFailed:
      'Geri bildirim taslağı yerel olarak hazırlandı, fakat harici issue bağlantısı açılamadı.',
    storageWarning:
      'Tarayıcı yerel depolaması taslağı kaydedemedi; issue bağlantısı yine de hazır.',
    technicalDetail: 'Teknik ayrıntı',
    openIssue: 'GitHub issue aç',
    genericError: 'Geri bildirim gönderilemedi.',
  },
};

export function getFeedbackCopy(locale: DocLanguage): FeedbackCopy {
  return feedbackCopy[locale];
}
