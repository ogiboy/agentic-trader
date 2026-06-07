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
