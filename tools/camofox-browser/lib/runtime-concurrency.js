export function normalizeUserId(userId) {
  return String(userId);
}

export function createRuntimeConcurrency({
  handlerTimeoutMs,
  healthState,
  maxConcurrentPerUser,
  tabLockQueueDepth,
  tabLockTimeoutMs = 35000,
  tabLockTimeoutsTotal,
}) {
  class TabLock {
    constructor() {
      this.queue = [];
      this.active = false;
    }

    acquire(timeoutMs) {
      return new Promise((resolve, reject) => {
        const entry = { resolve, reject, timer: null };
        entry.timer = setTimeout(() => {
          const idx = this.queue.indexOf(entry);
          if (idx !== -1) this.queue.splice(idx, 1);
          tabLockTimeoutsTotal.inc();
          refreshTabLockQueueDepth();
          reject(new Error('Tab lock queue timeout'));
        }, timeoutMs);
        this.queue.push(entry);
        refreshTabLockQueueDepth();
        this._tryNext();
      });
    }

    release() {
      this.active = false;
      this._tryNext();
      refreshTabLockQueueDepth();
    }

    _tryNext() {
      if (this.active || this.queue.length === 0) return;
      this.active = true;
      const entry = this.queue.shift();
      clearTimeout(entry.timer);
      refreshTabLockQueueDepth();
      entry.resolve();
    }

    drain() {
      this.active = true;
      for (const entry of this.queue) {
        clearTimeout(entry.timer);
        entry.reject(new Error('Tab destroyed'));
      }
      this.queue = [];
      refreshTabLockQueueDepth();
    }
  }

  const tabLocks = new Map();
  const userConcurrency = new Map();

  function getTabLock(tabId) {
    if (!tabLocks.has(tabId)) tabLocks.set(tabId, new TabLock());
    return tabLocks.get(tabId);
  }

  async function withTabLock(tabId, operation, timeoutMs = handlerTimeoutMs) {
    const lock = getTabLock(tabId);
    await lock.acquire(tabLockTimeoutMs);
    try {
      return await withTimeout(operation(), timeoutMs, 'action');
    } finally {
      lock.release();
    }
  }

  function withTimeout(promise, ms, label) {
    return Promise.race([
      promise,
      new Promise((_, reject) =>
        setTimeout(
          () => reject(new Error(`${label} timed out after ${ms}ms`)),
          ms,
        ),
      ),
    ]);
  }

  async function withUserLimit(userId, operation) {
    const key = normalizeUserId(userId);
    let state = userConcurrency.get(key);
    if (!state) {
      state = { active: 0, queue: [] };
      userConcurrency.set(key, state);
    }
    if (state.active >= maxConcurrentPerUser) {
      await new Promise((resolve, reject) => {
        const timer = setTimeout(
          () => reject(new Error('User concurrency limit reached, try again')),
          30000,
        );
        state.queue.push(() => {
          clearTimeout(timer);
          resolve();
        });
      });
    }
    state.active++;
    healthState.activeOps++;
    try {
      const result = await operation();
      healthState.lastSuccessfulNav = Date.now();
      return result;
    } finally {
      healthState.activeOps--;
      state.active--;
      if (state.queue.length > 0) {
        const next = state.queue.shift();
        next();
      }
      if (state.active === 0 && state.queue.length === 0) {
        userConcurrency.delete(key);
      }
    }
  }

  function clearSessionLocks(session) {
    if (!session?.tabGroups) return;
    for (const [, group] of session.tabGroups) {
      for (const tabId of group.keys()) {
        const lock = tabLocks.get(tabId);
        if (lock) {
          lock.drain();
          tabLocks.delete(tabId);
        }
      }
    }
    refreshTabLockQueueDepth();
  }

  function refreshTabLockQueueDepth() {
    let queued = 0;
    for (const lock of tabLocks.values()) {
      if (lock?.queue) queued += lock.queue.length;
    }
    tabLockQueueDepth.set(queued);
  }

  return {
    clearSessionLocks,
    refreshTabLockQueueDepth,
    tabLocks,
    withTabLock,
    withTimeout,
    withUserLimit,
  };
}
