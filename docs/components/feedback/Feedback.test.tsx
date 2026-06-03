// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { Feedback } from './Feedback';
import { FeedbackResult } from './FeedbackResult';
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '../ui/primitives/Card';

vi.mock('next/navigation', () => ({
  usePathname: () => '/en/docs/runtime',
}));

function createMemoryStorage(): Storage {
  const values = new Map<string, string>();

  return {
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => Array.from(values.keys())[index] ?? null,
    get length() {
      return values.size;
    },
    removeItem: (key) => {
      values.delete(key);
    },
    setItem: (key, value) => {
      values.set(key, String(value));
    },
  };
}

beforeEach(() => {
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: createMemoryStorage(),
  });
});

afterEach(() => {
  cleanup();
  localStorage.clear();
});

describe('docs feedback', () => {
  it('stores feedback locally and prepares a GitHub issue link', async () => {
    render(<Feedback locale='en' title='Runtime docs' />);

    const submit = screen.getByRole('button', { name: 'Prepare issue' });
    expect((submit as HTMLButtonElement).disabled).toBe(true);

    fireEvent.click(screen.getByRole('button', { name: 'Needs work' }));
    fireEvent.change(
      screen.getByPlaceholderText(
        'Tell us what was clear, missing, or confusing.',
      ),
      {
        target: { value: 'Missing broker setup example.' },
      },
    );
    fireEvent.click(submit);

    await screen.findByText(
      'Feedback draft is ready. Open the prefilled GitHub issue to submit it.',
    );

    const stored = JSON.parse(
      localStorage.getItem('agentic-trader-docs-feedback') ?? '[]',
    );
    expect(stored).toHaveLength(1);
    expect(stored[0]).toMatchObject({
      message: 'Missing broker setup example.',
      opinion: 'bad',
      title: 'Runtime docs',
      url: '/en/docs/runtime',
    });

    const issueLink = screen.getByRole('link', {
      name: 'Open GitHub issue',
    });
    const issueUrl = new URL(String(issueLink.getAttribute('href')));
    expect(issueUrl.searchParams.get('title')).toBe(
      'Docs feedback: Runtime docs',
    );
    expect(issueUrl.searchParams.get('body')).toContain(
      'Missing broker setup example.',
    );
  });

  it('renders localized result states and warning details', () => {
    render(
      <FeedbackResult
        locale='tr'
        result={{
          ok: true,
          storedAt: 'browser-memory',
          destination: 'github-issue',
          forwarding: 'failed',
          warning: 'Storage failed.',
        }}
      />,
    );

    expect(
      screen.getByText(
        'Geri bildirim taslağı yerel olarak hazırlandı, fakat harici issue bağlantısı açılamadı.',
      ),
    ).toBeTruthy();
    expect(screen.getByText('Teknik ayrıntı:')).toBeTruthy();
    expect(screen.getByText('Storage failed.')).toBeTruthy();

    cleanup();

    render(
      <FeedbackResult
        locale='en'
        result={{ ok: false, error: 'Feedback is invalid.' }}
      />,
    );

    expect(screen.getByText('Feedback is invalid.')).toBeTruthy();
  });
});

describe('docs card primitives', () => {
  it('renders every card slot with merged classes and size state', () => {
    render(
      <Card className='custom-card' size='sm'>
        <CardHeader>
          <CardTitle>Title</CardTitle>
          <CardDescription>Description</CardDescription>
          <CardAction>Action</CardAction>
        </CardHeader>
        <CardContent>Content</CardContent>
        <CardFooter>Footer</CardFooter>
      </Card>,
    );

    const card = screen.getByText('Title').closest('[data-slot="card"]');
    expect(card?.getAttribute('data-size')).toBe('sm');
    expect(card?.className).toContain('custom-card');
    expect(screen.getByText('Description')).toBeTruthy();
    expect(screen.getByText('Action')).toBeTruthy();
    expect(screen.getByText('Content')).toBeTruthy();
    expect(screen.getByText('Footer')).toBeTruthy();
  });
});
