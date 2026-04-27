import { ShieldCheck } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import type { DocLanguage } from '@/lib/i18n/config';

type RepoGuardrailAlertProps = {
  locale: DocLanguage;
  text: string;
};

const titles: Record<DocLanguage, string> = {
  en: 'Repo guardrail',
  tr: 'Depo koruma sınırı',
};

export function RepoGuardrailAlert({
  locale,
  text,
}: Readonly<RepoGuardrailAlertProps>) {
  return (
    <Alert className="docs-home-panel">
      <ShieldCheck className="size-4" />
      <AlertTitle>{titles[locale]}</AlertTitle>
      <AlertDescription>{text}</AlertDescription>
    </Alert>
  );
}
