// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { Alert, AlertAction, AlertDescription, AlertTitle } from './Alert';
import { Badge } from './Badge';
import { Separator } from './Separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './Tabs';

afterEach(() => {
  cleanup();
});

describe('docs ui primitives', () => {
  it('renders alert, badge, separator, and tabs slots', () => {
    render(
      <>
        <Alert className='custom-alert' variant='destructive'>
          <AlertTitle>Release warning</AlertTitle>
          <AlertDescription>Review the changelog before merging.</AlertDescription>
          <AlertAction>Open</AlertAction>
        </Alert>
        <Badge variant='outline'>Stable</Badge>
        <Badge asChild variant='link'>
          <a href='https://example.com/docs'>Docs link</a>
        </Badge>
        <Separator decorative={false} orientation='vertical' />
        <Tabs defaultValue='overview' orientation='vertical'>
          <TabsList variant='line'>
            <TabsTrigger value='overview'>Overview</TabsTrigger>
            <TabsTrigger value='runtime'>Runtime</TabsTrigger>
          </TabsList>
          <TabsContent value='overview'>Overview panel</TabsContent>
        </Tabs>
      </>,
    );

    const alert = screen.getByRole('alert');
    expect(alert.className).toContain('custom-alert');
    expect(screen.getByText('Release warning')).toBeTruthy();
    expect(screen.getByText('Open')).toBeTruthy();
    expect(screen.getByText('Stable').getAttribute('data-variant')).toBe(
      'outline',
    );
    expect(screen.getByRole('link', { name: 'Docs link' })).toBeTruthy();
    expect(screen.getByText('Overview panel')).toBeTruthy();
  });
});
