import crypto from 'node:crypto';
import { actionFromReq } from './request-utils.js';

export function createRequestLoggingMiddleware({
  log,
  reporter,
  requestDuration,
  requestsTotal,
}) {
  return (req, res, next) => {
    const reqId = crypto.randomUUID().slice(0, 8);
    req.reqId = reqId;
    req.startTime = Date.now();

    const userId = req.body?.userId || req.query?.userId || '-';
    if (req.path !== '/health') {
      log('info', 'req', {
        reqId,
        method: req.method,
        path: req.path,
        userId,
      });
    }

    const action = actionFromReq(req);
    reporter.trackRoute(`${req.method} ${req.route?.path || '[unmatched]'}`);
    const done = requestDuration.startTimer({ action });

    const origEnd = res.end.bind(res);
    res.end = function (...args) {
      const ms = Date.now() - req.startTime;
      const isErrorStatus = res.statusCode >= 400;
      requestsTotal.labels(action, isErrorStatus ? 'error' : 'success').inc();
      done();

      if (req.path !== '/health') {
        log('info', 'res', { reqId, status: res.statusCode, ms });
      }

      return origEnd(...args);
    };

    next();
  };
}
