/**
 * @openapi
 * /health:
 *   get:
 *     tags: [System]
 *     summary: Health check
 *     description: Detailed health with tab/session counts and failure tracking.
 *     responses:
 *       200:
 *         description: Healthy.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 ok:
 *                   type: boolean
 *                 engine:
 *                   type: string
 *                 browserConnected:
 *                   type: boolean
 *                 browserRunning:
 *                   type: boolean
 *                 activeTabs:
 *                   type: integer
 *                 activeSessions:
 *                   type: integer
 *                 consecutiveFailures:
 *                   type: integer
 *       503:
 *         description: Unhealthy or recovering.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 ok:
 *                   type: boolean
 *                 recovering:
 *                   type: boolean
 */
function mountHealthRoute(app, ctx) {
  app.get('/health', (req, res) => {
    if (ctx.healthState.isRecovering) {
      return res
        .status(503)
        .json({ ok: false, engine: 'camoufox', recovering: true });
    }
    const running = ctx.getBrowserRunning();
    if (ctx.proxyPool?.canRotateSessions && !running) {
      ctx.scheduleBrowserWarmRetry();
      return res.status(503).json({
        ok: false,
        engine: 'camoufox',
        browserConnected: false,
        browserRunning: false,
        warming: true,
        ...(ctx.flyMachineId ? { machineId: ctx.flyMachineId } : {}),
      });
    }
    const mem = process.memoryUsage();
    const rssMb = Math.round(mem.rss / 1048576);
    const heapUsedMb = Math.round(mem.heapUsed / 1048576);
    const nativeMemMb = rssMb - heapUsedMb;
    res.json({
      ok: true,
      engine: 'camoufox',
      browserConnected: running,
      browserRunning: running,
      activeTabs: ctx.getTotalTabCount(),
      activeSessions: ctx.sessions.size,
      consecutiveFailures: ctx.healthState.consecutiveNavFailures,
      memory: { rssMb, heapUsedMb, nativeMemMb },
      ...(ctx.flyMachineId ? { machineId: ctx.flyMachineId } : {}),
    });
  });
}

/**
 * @openapi
 * /metrics:
 *   get:
 *     tags: [System]
 *     summary: Prometheus metrics
 *     description: Returns Prometheus text exposition format. Requires PROMETHEUS_ENABLED=1.
 *     responses:
 *       200:
 *         description: Prometheus metrics.
 *         content:
 *           text/plain:
 *             schema:
 *               type: string
 *       404:
 *         description: Metrics disabled.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
function mountMetricsRoute(app, ctx) {
  app.get('/metrics', async (_req, res) => {
    const reg = ctx.getRegister();
    if (!reg) {
      res.status(404).json({
        error:
          'Prometheus metrics disabled. Set PROMETHEUS_ENABLED=1 to enable.',
      });
      return;
    }
    res.set('Content-Type', reg.contentType);
    res.send(await reg.metrics());
  });
}

export function mountSystemRoutes(app, ctx) {
  mountHealthRoute(app, ctx);
  mountMetricsRoute(app, ctx);
}
