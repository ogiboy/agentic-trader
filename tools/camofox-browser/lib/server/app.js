import express from 'express';
import {
  accessKeyMiddleware,
  requireAuth,
  timingSafeCompare,
} from '../auth.js';
import { createFlyHelpers } from '../fly.js';
import { createRequestLoggingMiddleware } from '../request-logging.js';

export function createServerApp({
  config,
  log,
  reporter,
  requestDuration,
  requestsTotal,
}) {
  const app = express();
  app.use(express.json({ limit: '100kb' }));

  const authMiddleware = () => requireAuth(config);
  const fly = createFlyHelpers(config);
  app.use('/tabs/:tabId', fly.replayMiddleware(log));
  app.use(accessKeyMiddleware(config));
  app.use(
    createRequestLoggingMiddleware({
      log,
      reporter,
      requestDuration,
      requestsTotal,
    }),
  );

  return {
    app,
    authMiddleware,
    fly,
    flyMachineId: fly.machineId,
    timingSafeCompare,
  };
}
