import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import type { HomeCurrentFocus } from '@/lib/home/content/types';
import { Bot, FileSearch, LayoutPanelTop } from 'lucide-react';

type CurrentFocusPanelProps = {
  focus: HomeCurrentFocus;
};

const icons = {
  bot: Bot,
  layout: LayoutPanelTop,
  inspect: FileSearch,
} as const;

export function CurrentFocusPanel({
  focus,
}: Readonly<CurrentFocusPanelProps>) {
  return (
    <Card className='docs-home-panel sticky top-6'>
      <CardHeader>
        <CardTitle>{focus.title}</CardTitle>
        <CardDescription>{focus.description}</CardDescription>
      </CardHeader>
      <CardContent className='flex flex-col gap-4 text-sm text-muted-foreground'>
        {focus.items.map((item, index) => {
          const Icon = icons[item.icon];

          return (
            <div
              key={`${item.icon}-${index}`}
              className='flex items-start gap-3'
            >
              <Icon className='mt-0.5 size-4 text-primary' />
              {item.text}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
