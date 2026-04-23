import type { DocLanguage } from "@/lib/i18n/config";

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
  successForwarded: string;
  successLocalOnlyDisabled: string;
  successLocalOnlyFailed: string;
  technicalDetail: string;
  openDiscussion: string;
  genericError: string;
};

const feedbackCopy: Record<DocLanguage, FeedbackCopy> = {
  en: {
    title: "How was this page?",
    description:
      "Every submission is always written to `runtime/docs-feedback.jsonl`. If `docs/.env.local` contains GitHub App credentials, the same submission is also forwarded to GitHub Discussions for the matching page.",
    helpful: "Helpful",
    needsWork: "Needs work",
    noteLabel: "Optional note",
    notePlaceholder: "Tell us what was clear, missing, or confusing.",
    destinationSummary:
      "Always stores a local feedback log. When GitHub forwarding is configured, it also opens or comments on the matching discussion thread.",
    submit: "Send feedback",
    saving: "Saving feedback...",
    successForwarded:
      "Saved to the local feedback log and forwarded to GitHub Discussions.",
    successLocalOnlyDisabled:
      "Saved to the local feedback log. GitHub Discussions forwarding is not configured for this docs instance.",
    successLocalOnlyFailed:
      "Saved to the local feedback log. GitHub Discussions forwarding failed for this submission.",
    technicalDetail: "Technical detail",
    openDiscussion: "Open GitHub discussion",
    genericError: "Failed to send feedback.",
  },
  tr: {
    title: "Bu sayfa nasıl?",
    description:
      "Her gönderim her zaman `runtime/docs-feedback.jsonl` dosyasına yazılır. `docs/.env.local` içinde GitHub App bilgileri varsa aynı gönderim ilgili sayfa için GitHub Discussions'a da iletilir.",
    helpful: "İşe yaradı",
    needsWork: "Geliştirilmeli",
    noteLabel: "İsteğe bağlı not",
    notePlaceholder: "Neyin açık, eksik veya kafa karıştırıcı olduğunu yaz.",
    destinationSummary:
      "Her zaman yerel bir feedback kaydı tutar. GitHub forwarding açıksa aynı kayıt ilgili tartışma başlığına da gider.",
    submit: "Geri bildirim gönder",
    saving: "Geri bildirim kaydediliyor...",
    successForwarded:
      "Yerel feedback kaydına yazıldı ve GitHub Discussions'a iletildi.",
    successLocalOnlyDisabled:
      "Yerel feedback kaydına yazıldı. Bu docs örneğinde GitHub Discussions forwarding yapılandırılmamış.",
    successLocalOnlyFailed:
      "Yerel feedback kaydına yazıldı. Bu gönderim için GitHub Discussions forwarding başarısız oldu.",
    technicalDetail: "Teknik ayrıntı",
    openDiscussion: "GitHub tartışmasını aç",
    genericError: "Geri bildirim gönderilemedi.",
  },
};

export function getFeedbackCopy(locale: DocLanguage): FeedbackCopy {
  return feedbackCopy[locale];
}
