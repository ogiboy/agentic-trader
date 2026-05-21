import { useCallback, useEffect, useRef } from 'react';

import type { DashboardData } from '../control-room.helpers';
import {
  errorMessage,
  isDashboardRequestCurrent,
  readJson,
  WebguiHttpError,
  type DashboardRequestContext,
} from './api';

type BusyRef = {
  current: string | null;
};

type DashboardPollingProps = {
  applyDashboardPayload: (payload: DashboardData) => void;
  busyRef: BusyRef;
  setAuthError: (error: string | null) => void;
  setAuthRequired: (required: boolean) => void;
  setDashboard: (dashboard: DashboardData | null) => void;
  setError: (error: string | null) => void;
  setLoading: (loading: boolean) => void;
};

export type DashboardLoader = (options?: { force?: boolean }) => Promise<void>;

export function useDashboardPolling({
  applyDashboardPayload,
  busyRef,
  setAuthError,
  setAuthRequired,
  setDashboard,
  setError,
  setLoading,
}: DashboardPollingProps) {
  const lastRequestSeqRef = useRef(0);
  const dashboardAbortRef = useRef<AbortController | null>(null);

  const abortDashboardRequest = useCallback(() => {
    dashboardAbortRef.current?.abort();
    dashboardAbortRef.current = null;
  }, []);

  const applyLatestDashboard = useCallback(
    (payload: DashboardData) => {
      lastRequestSeqRef.current += 1;
      abortDashboardRequest();
      applyDashboardPayload(payload);
      setLoading(false);
    },
    [abortDashboardRequest, applyDashboardPayload, setLoading],
  );

  const beginDashboardRequest = useCallback(
    (force: boolean): DashboardRequestContext | null => {
      if (!force && busyRef.current) {
        return null;
      }
      const activeRequest = dashboardAbortRef.current;
      if (activeRequest && !activeRequest.signal.aborted) {
        if (!force) {
          return null;
        }
        activeRequest.abort();
      }
      const seq = lastRequestSeqRef.current + 1;
      lastRequestSeqRef.current = seq;
      const controller = new AbortController();
      dashboardAbortRef.current = controller;
      return { controller, seq };
    },
    [busyRef],
  );

  const completeDashboardRequest = useCallback(
    ({ controller, seq }: DashboardRequestContext) => {
      if (dashboardAbortRef.current === controller) {
        dashboardAbortRef.current = null;
      }
      if (seq === lastRequestSeqRef.current) {
        setLoading(false);
      }
    },
    [setLoading],
  );

  const loadDashboard = useCallback<DashboardLoader>(
    async ({ force = false }: { force?: boolean } = {}) => {
      const request = beginDashboardRequest(force);
      if (!request) {
        return;
      }
      try {
        const payload = await readJson<DashboardData>('/api/dashboard', {
          signal: request.controller.signal,
        });
        if (!isDashboardRequestCurrent(request, lastRequestSeqRef.current)) {
          return;
        }
        applyDashboardPayload(payload);
      } catch (nextError) {
        if (!isDashboardRequestCurrent(request, lastRequestSeqRef.current)) {
          return;
        }
        if (nextError instanceof WebguiHttpError && nextError.status === 401) {
          setAuthRequired(true);
          setAuthError(null);
          setDashboard(null);
          return;
        }
        setError(errorMessage(nextError));
      } finally {
        completeDashboardRequest(request);
      }
    },
    [
      applyDashboardPayload,
      beginDashboardRequest,
      completeDashboardRequest,
      setAuthError,
      setAuthRequired,
      setDashboard,
      setError,
    ],
  );

  useEffect(() => {
    const initialRefresh = setTimeout(() => {
      void loadDashboard();
    }, 0);
    const timer = setInterval(() => {
      void loadDashboard();
    }, 2500);
    return () => {
      clearTimeout(initialRefresh);
      clearInterval(timer);
      abortDashboardRequest();
    };
  }, [abortDashboardRequest, loadDashboard]);

  return {
    abortDashboardRequest,
    applyLatestDashboard,
    loadDashboard,
  };
}
