import { describe, expect, it, vi } from 'vitest';

describe('docs configuration helpers', () => {
  it('normalizes the configured base path for metadata assets', async () => {
    vi.resetModules();
    vi.stubEnv('NEXT_PUBLIC_BASE_PATH', ' docs/ ');
    const metadata = await import('./site-metadata.ts');

    expect(metadata.basePath).toBe('/docs');
    expect(metadata.docsMetadata.manifest).toBe('/docs/site.webmanifest');
    expect(metadata.docsMetadata.icons.shortcut).toBe('/docs/favicon.ico');

    vi.unstubAllEnvs();
  });

  it('falls back to English for unknown documentation locales', async () => {
    const config = await import('./i18n/config.ts');

    expect(config.docLanguages).toEqual(['en', 'tr']);
    expect(config.getDocLanguage('tr')).toBe('tr');
    expect(config.getDocLanguage('fr')).toBe('en');
    expect(config.getHomeMetadata('en').title).toBe('Agentic Trader Docs');
    expect(config.getHomeMetadata('tr').title).toBe('Agentic Trader Dokümantasyonu');
  });
});
