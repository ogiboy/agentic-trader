import type { ReactNode, SyntheticEvent } from 'react';

import type { KeyValueItems, PanelAccent } from '../control-room.helpers';
import { cx } from '../control-room.helpers';
import type { ControlRoomCopy } from './labels';

/**
 * Render a titled panel section with optional accent styling.
 *
 * @param accent - Optional accent color; one of `"lime"`, `"amber"`, `"cyan"`, or `"rose"`. When provided, applies the `panel--{accent}` modifier class.
 * @returns The section element containing the panel title and body.
 */
export function Panel({
  title,
  accent,
  children,
}: Readonly<{
  title: string;
  accent?: PanelAccent;
  children: ReactNode;
}>) {
  return (
    <section className={cx('panel', accent ? `panel--${accent}` : undefined)}>
      <div className='panel__title'>{title}</div>
      <div className='panel__body'>{children}</div>
    </section>
  );
}

/**
 * Renders a description list (`dl`) of label/value pairs as a key/value list.
 *
 * @param items - An array of `[label, value]` string tuples to render as `dt`/`dd` rows.
 * @returns A `<dl>` element containing one row per tuple, each with a `dt` for the label and a `dd` for the value.
 */
export function KeyValueList({ items }: Readonly<{ items: KeyValueItems }>) {
  return (
    <dl className='kv-list'>
      {items.map(([label, value]) => (
        <div className='kv-list__row' key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

/**
 * Render an unordered list from an array of strings.
 *
 * @param items - Array of text entries to display as list items.
 * @returns A `<ul>` element whose children are `<li>` elements for each string in `items`.
 */
export function TextList({ items }: Readonly<{ items: string[] }>) {
  return (
    <ul className='text-list'>
      {items.map((item, index) => (
        <li key={`${item}-${index}`}>{item}</li>
      ))}
    </ul>
  );
}

/**
 * Renders a pretty-printed JSON representation of `value` inside a <pre> element.
 *
 * @param value - The value to serialize as formatted JSON for display.
 * @returns A React element containing the formatted JSON.
 */
export function JsonPreview({ value }: Readonly<{ value: unknown }>) {
  return <pre className='json-preview'>{JSON.stringify(value, null, 2)}</pre>;
}

export function WebguiTokenPrompt({
  busy,
  copy,
  error,
  token,
  onSubmit,
  onTokenChange,
}: Readonly<{
  busy: boolean;
  copy: ControlRoomCopy['auth'];
  error: string | null;
  token: string;
  onSubmit: (event: SyntheticEvent<HTMLFormElement>) => void;
  onTokenChange: (value: string) => void;
}>) {
  return (
    <section className='auth-panel' aria-labelledby='webgui-token-title'>
      <div className='auth-panel__header'>
        <div className='sidebar__eyebrow'>{copy.eyebrow}</div>
        <h1 id='webgui-token-title'>{copy.title}</h1>
        <p>{copy.body}</p>
      </div>
      <form className='auth-panel__form' onSubmit={onSubmit}>
        <label className='field-label'>
          <span>{copy.tokenLabel}</span>
          <input
            autoComplete='off'
            autoFocus
            onChange={(event) => onTokenChange(event.target.value)}
            type='password'
            value={token}
          />
        </label>
        {error ? <div className='banner banner--bad'>{error}</div> : null}
        <button
          className='button button--solid'
          disabled={busy || !token.trim()}
          type='submit'
        >
          {busy ? copy.unlocking : copy.unlock}
        </button>
      </form>
    </section>
  );
}
