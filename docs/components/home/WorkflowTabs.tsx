import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/primitives/Card';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/primitives/Tabs';
import type { WorkflowTrack } from '@/lib/home/content/types';

type WorkflowTabsProps = {
  note: string;
  tracks: WorkflowTrack[];
};

/**
 * Renders a tabbed workflow panel where each track becomes a tab containing cards, with a footer note below.
 *
 * @param note - Text displayed below the tabs as a muted footer note.
 * @param tracks - Array of workflow tracks; each track's `label` is used for the tab trigger and its `cards` populate the tab content.
 * @returns The section element containing the tabs, their card contents, and the footer note.
 */
export function WorkflowTabs({ note, tracks }: Readonly<WorkflowTabsProps>) {
  return (
    <section className='docs-home-panel p-6 sm:p-8'>
      <Tabs className='flex flex-col gap-6' defaultValue={tracks[0]?.id}>
        <TabsList className='w-full justify-start'>
          {tracks.map((track) => (
            <TabsTrigger key={track.id} value={track.id}>
              {track.label}
            </TabsTrigger>
          ))}
        </TabsList>
        {tracks.map((track) => (
          <TabsContent key={track.id} className='m-0' value={track.id}>
            <div className='grid gap-4 lg:grid-cols-3'>
              {track.cards.map((card) => (
                <Card key={card.title}>
                  <CardHeader>
                    <CardTitle className='text-base'>{card.title}</CardTitle>
                  </CardHeader>
                  <CardContent className='text-sm text-muted-foreground'>
                    {card.body}
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>
        ))}
      </Tabs>
      <p className='mt-5 text-sm text-muted-foreground'>{note}</p>
    </section>
  );
}
