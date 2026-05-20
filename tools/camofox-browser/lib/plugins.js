/**
 * Camofox-browser plugin system.
 *
 * Plugins live in plugins/<name>/index.js and export a register(app, ctx) function.
 * The ctx object provides access to sessions, config, logging, auth middleware,
 * core functions, and an EventEmitter for lifecycle hooks.
 *
 * 29 events across 7 categories:
 *
 *   BROWSER LIFECYCLE
 *     browser:launching       { options }                      -- mutate launch options
 *     browser:launched        { browser, display }             -- after launch
 *     browser:restart         { reason }                       -- before restart cycle
 *     browser:closed          { reason }                       -- after browser closed
 *     browser:error           { error }                        -- uncaught browser error
 *
 *   SESSION LIFECYCLE
 *     session:creating        { userId, contextOptions }       -- mutate context options
 *     session:created         { userId, context }              -- after context stored
 *     session:destroying      { userId, reason }               -- before context close (context still alive)
 *     session:destroyed       { userId, reason }               -- after cleanup
 *     session:expired         { userId, idleMs }               -- reaper triggered
 *
 *   TAB LIFECYCLE
 *     tab:created             { userId, tabId, page, url }
 *     tab:navigated           { userId, tabId, url, prevUrl }
 *     tab:destroyed           { userId, tabId, reason }
 *     tab:recycled            { userId, tabId }
 *     tab:error               { userId, tabId, error }
 *
 *   CONTENT
 *     tab:snapshot            { userId, tabId, snapshot }
 *     tab:screenshot          { userId, tabId, buffer }
 *     tab:evaluate            { userId, tabId, expression }
 *     tab:evaluated           { userId, tabId, result }
 *
 *   INPUT
 *     tab:click               { userId, tabId, ref, selector }
 *     tab:type                { userId, tabId, text, ref, mode }
 *     tab:scroll              { userId, tabId, direction, amount }
 *     tab:press               { userId, tabId, key }
 *
 *   DOWNLOADS
 *     tab:download:start      { userId, tabId, filename, url }
 *     tab:download:complete   { userId, tabId, filename, path, size }
 *
 *   COOKIES / AUTH
 *     session:cookies:import  { userId, count }
 *     session:storage:export  { userId }
 *
 *   SERVER
 *     server:starting         { port }
 *     server:started          { port, pid }
 *     server:shutdown         { signal }
 *
 * Mutating hooks (browser:launching, session:creating) pass the options object
 * by reference -- plugins can modify it in place before core uses it.
 */

import { EventEmitter } from 'events';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.join(__dirname, '..');
const PLUGINS_DIR = path.join(ROOT_DIR, 'plugins');
const CONFIG_PATH = path.join(ROOT_DIR, 'camofox.config.json');

/**
 * Read plugin configuration from camofox.config.json and derive the allowed plugin list and per-plugin configuration map.
 *
 * Supports two shapes for the `plugins` field in the config file:
 * - An array of plugin names → returns that array as `list` and an empty `configs` map.
 * - An object mapping plugin names to booleans or config objects → includes names whose value is not `false` (and not an object with `enabled === false`) in `list`, and stores any object values in `configs`.
 * @returns {{list: string[]|null, configs: Map<string, object>}} `list` is an array of allowed plugin names or `null` when no explicit list is present; `configs` is a Map of per-plugin configuration objects keyed by plugin name.
 */
function readPluginConfig() {
  const configs = new Map();
  try {
    const raw = fs.readFileSync(CONFIG_PATH, 'utf-8');
    const config = JSON.parse(raw);
    if (!config.plugins) return { list: null, configs };
    if (Array.isArray(config.plugins)) {
      return { list: config.plugins, configs };
    }
    if (typeof config.plugins === 'object') {
      const list = [];
      for (const [name, pluginConf] of Object.entries(config.plugins)) {
        if (
          pluginConf === false ||
          (typeof pluginConf === 'object' && pluginConf.enabled === false)
        )
          continue;
        list.push(name);
        if (typeof pluginConf === 'object') configs.set(name, pluginConf);
      }
      return { list, configs };
    }
  } catch {}
  return { list: null, configs };
}

/**
 * Create an EventEmitter used for plugin lifecycle hooks.
 *
 * The emitter's maximum listener count is increased to 50. Adds an
 * `emitAsync(eventName, payload)` method that calls the current listeners
 * for `eventName` in parallel and awaits their completion.
 *
 * @returns {EventEmitter} The EventEmitter extended with an `emitAsync(eventName, payload)` method.
 */
export function createPluginEvents() {
  const events = new EventEmitter();
  events.setMaxListeners(50); // generous for many plugins

  /**
   * Emit an event and await all listeners (including async ones).
   * Use for mutating hooks where plugins must finish before core continues.
   * Regular emit() is still used for fire-and-forget observational events.
   */
  events.emitAsync = async function emitAsync(eventName, payload) {
    const listeners = this.listeners(eventName);
    await Promise.all(listeners.map((fn) => fn(payload)));
  };

  return events;
}

/**
 * Load and register all plugins from plugins/<name>/index.js.
 *
 * @param {object} app - Express app
 * @param {object} ctx - Plugin context: { sessions, config, log, events, auth, ensureBrowser, getSession, destroySession }
 *                       Mutable -- plugins can replace ctx.createVirtualDisplay etc.
 * @returns {string[]} - Names of loaded plugins
 */
export async function loadPlugins(app, ctx) {
  const loaded = [];

  if (!fs.existsSync(PLUGINS_DIR)) {
    ctx.log('info', 'no plugins directory found, skipping plugin load');
    return loaded;
  }

  const { list: allowList, configs: pluginConfigs } = readPluginConfig();
  const entries = fs.readdirSync(PLUGINS_DIR, { withFileTypes: true });

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const name = entry.name;

    // Skip directories starting with _ or .
    if (name.startsWith('_') || name.startsWith('.')) continue;

    // If camofox.config.json specifies a plugins list, only load those
    if (allowList && !allowList.includes(name)) {
      ctx.log(
        'debug',
        `plugin "${name}" not in camofox.config.json plugins list, skipping`,
      );
      continue;
    }

    const indexPath = path.join(PLUGINS_DIR, name, 'index.js');
    if (!fs.existsSync(indexPath)) {
      ctx.log('warn', `plugin "${name}" has no index.js, skipping`);
      continue;
    }

    try {
      const mod = await import(indexPath);
      const register = mod.default || mod.register;
      if (typeof register !== 'function') {
        ctx.log(
          'warn',
          `plugin "${name}" does not export a register function, skipping`,
        );
        continue;
      }

      const pluginConfig = pluginConfigs.get(name) || {};
      await register(app, ctx, pluginConfig);
      loaded.push(name);
      ctx.log('info', 'plugin loaded', { plugin: name });
    } catch (err) {
      ctx.log('error', 'plugin load failed', {
        plugin: name,
        error: err.message,
        stack: err.stack,
      });
    }
  }

  return loaded;
}
