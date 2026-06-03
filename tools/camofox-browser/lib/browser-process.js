import fs from 'node:fs';
import os from 'node:os';

export function createBrowserProcess({
  cleanupStaleFirefoxProfiles,
  getBrowser,
  getLastBrowserPid,
  log,
  pageCloseTimeoutMs,
  reporter,
  resetNativeMemBaseline,
  setBrowser,
  setLastBrowserPid,
}) {
  let browserClosePromise = null;

  async function safePageClose(page) {
    try {
      await Promise.race([
        page.close(),
        new Promise((resolve) => setTimeout(resolve, pageCloseTimeoutMs)),
      ]);
    } catch (e) {
      log('warn', 'page close failed', { error: e.message });
    }
  }

  function getHostOS() {
    const platform = os.platform();
    if (platform === 'darwin') return 'macos';
    if (platform === 'win32') return 'windows';
    return 'linux';
  }

  async function closeBrowserFully(reason) {
    if (browserClosePromise) return browserClosePromise;
    browserClosePromise = closeBrowserFullyImpl(reason);
    try {
      return await browserClosePromise;
    } finally {
      browserClosePromise = null;
    }
  }

  async function closeBrowserFullyImpl(reason) {
    const b = getBrowser();
    if (!b) return;

    const pid = getLastBrowserPid();
    const preCloseFds = countOpenFds();
    const preCloseHandles = countActiveHandles();

    setBrowser(null);
    setLastBrowserPid(null);

    let closeTimer;
    try {
      await Promise.race([
        b.close(),
        new Promise((_, reject) => {
          closeTimer = setTimeout(
            () => reject(new Error('browser.close() timeout')),
            10000,
          );
        }),
      ]);
    } catch (err) {
      log('warn', 'browser.close() failed or timed out', {
        reason,
        error: err.message,
        pid,
      });
    } finally {
      clearTimeout(closeTimer);
    }

    if (pid) {
      await forceKillProcessTree(pid, reason);
    }

    try {
      const cleaned = cleanupStaleFirefoxProfiles();
      if (cleaned.removed > 0) {
        log(
          'info',
          'cleaned stale firefox profiles after browser close',
          cleaned,
        );
      }
    } catch {
      // Best effort cleanup.
    }

    reporter.resetNativeMemBaseline();
    resetNativeMemBaseline();

    const postCloseFds = countOpenFds();
    const postCloseHandles = countActiveHandles();
    if (postCloseFds !== null && preCloseFds !== null) {
      const fdDelta = postCloseFds - preCloseFds;
      if (fdDelta > 10) {
        log('warn', 'FD leak detected after browser close', {
          reason,
          preCloseFds,
          postCloseFds,
          delta: fdDelta,
          preCloseHandles,
          postCloseHandles,
        });
      }
    }
    log('info', 'browser closed fully', {
      reason,
      pid,
      preCloseFds,
      postCloseFds,
      preCloseHandles,
      postCloseHandles,
    });
  }

  async function forceKillProcessTree(pid, reason) {
    if (!pid || pid <= 1) return;

    try {
      process.kill(pid, 'SIGKILL');
      log('info', 'sent SIGKILL to browser process', { pid, reason });
    } catch (err) {
      if (err.code !== 'ESRCH') {
        log('warn', 'failed to kill browser process', {
          pid,
          error: err.message,
        });
      }
    }

    try {
      process.kill(-pid, 'SIGKILL');
    } catch {
      // ESRCH means the process group does not exist, which is acceptable.
    }

    await new Promise((r) => setTimeout(r, 200));

    if (process.platform === 'linux') {
      const myPid = process.pid;
      const currentBrowserPid = getLastBrowserPid();
      try {
        const procDirs = fs.readdirSync('/proc').filter((d) => /^\d+$/.test(d));
        const orphans = [];
        for (const procPid of procDirs) {
          const numPid = parseInt(procPid);
          if (numPid === myPid || numPid === pid || numPid === currentBrowserPid)
            continue;
          try {
            const status = fs.readFileSync(`/proc/${procPid}/status`, 'utf8');
            const ppidMatch = status.match(/PPid:\s+(\d+)/);
            const ppid = ppidMatch ? parseInt(ppidMatch[1]) : -1;
            if (ppid === 1 || ppid === myPid) {
              const cmdline = fs.readFileSync(
                `/proc/${procPid}/cmdline`,
                'utf8',
              );
              if (
                /firefox-esr|firefox|camoufox|libxul\.so|GeckoChildProcess/i.test(
                  cmdline,
                )
              ) {
                orphans.push(numPid);
              }
            }
          } catch {
            // Process vanished or permission denied.
          }
        }
        if (orphans.length > 0) {
          log('warn', 'killing orphaned browser child processes', {
            orphans,
            reason,
          });
          for (const orphanPid of orphans) {
            try {
              process.kill(orphanPid, 'SIGKILL');
            } catch {
              // Already dead.
            }
          }
        }
      } catch (err) {
        log('warn', 'failed to scan for orphaned browser processes', {
          error: err.message,
        });
      }
    }

    await new Promise((r) => setTimeout(r, 300));
  }

  function countOpenFds() {
    try {
      if (process.platform === 'linux')
        return fs.readdirSync('/proc/self/fd').length;
    } catch {
      // Unavailable.
    }
    return null;
  }

  function countActiveHandles() {
    try {
      return process._getActiveHandles().length;
    } catch {
      return null;
    }
  }

  return { closeBrowserFully, getHostOS, safePageClose };
}
