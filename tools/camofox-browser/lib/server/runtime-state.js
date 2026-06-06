/**
 * Create a mutable runtime state container for browser, plugin, memory baseline and session data.
 *
 * The returned object exposes a `sessions` Map and accessor/mutator functions for:
 * - `browser`
 * - `lastBrowserPid`
 * - `nativeMemBaseline` (plus `resetNativeMemBaseline()` to clear it to `null`)
 * - `pluginContext`
 *
 * @returns {{sessions: Map<any, any>, getBrowser: function(): any, setBrowser: function(any): void, getLastBrowserPid: function(): any, setLastBrowserPid: function(any): void, getNativeMemBaseline: function(): any, setNativeMemBaseline: function(any): void, resetNativeMemBaseline: function(): void, getPluginContext: function(): any, setPluginContext: function(any): void}} An object providing the mutable runtime state and accessor/mutator functions.
 */
export function createMutableRuntimeState() {
  let browser = null;
  let lastBrowserPid = null;
  let nativeMemBaseline = null;
  let pluginContext = null;
  const sessions = new Map();

  return {
    sessions,
    getBrowser: () => browser,
    setBrowser: (value) => {
      browser = value;
    },
    getLastBrowserPid: () => lastBrowserPid,
    setLastBrowserPid: (value) => {
      lastBrowserPid = value;
    },
    getNativeMemBaseline: () => nativeMemBaseline,
    setNativeMemBaseline: (value) => {
      nativeMemBaseline = value;
    },
    resetNativeMemBaseline: () => {
      nativeMemBaseline = null;
    },
    getPluginContext: () => pluginContext,
    setPluginContext: (value) => {
      pluginContext = value;
    },
  };
}
