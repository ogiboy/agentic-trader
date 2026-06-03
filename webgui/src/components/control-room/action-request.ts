import type { DashboardData } from '../control-room.helpers';
import { readJson, WebguiHttpError } from './api';
import type { ControlRoomMessage } from './Shell';

export type SetState<T> = (value: T) => void;

export type DashboardMutationOptions = {
  endpoint: string;
  body: Record<string, unknown>;
  applyLatestDashboard: (payload: DashboardData) => void;
  setAuthRequired: SetState<boolean>;
  setMessage: SetState<ControlRoomMessage | null>;
  onSuccess?: () => void;
};

export function messageFromError(nextError: unknown): string {
  return nextError instanceof Error ? nextError.message : String(nextError);
}

export function markAuthRequiredOnUnauthorized(
  nextError: unknown,
  setAuthRequired: SetState<boolean>,
): void {
  if (nextError instanceof WebguiHttpError && nextError.status === 401) {
    setAuthRequired(true);
  }
}

export async function runDashboardMutation({
  endpoint,
  body,
  applyLatestDashboard,
  setAuthRequired,
  setMessage,
  onSuccess,
}: DashboardMutationOptions): Promise<void> {
  try {
    const result = await readJson<{
      message: string;
      dashboard: DashboardData;
    }>(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
    });
    applyLatestDashboard(result.dashboard);
    onSuccess?.();
    setMessage({ text: result.message, tone: 'good' });
  } catch (nextError) {
    markAuthRequiredOnUnauthorized(nextError, setAuthRequired);
    setMessage({
      text: messageFromError(nextError),
      tone: 'bad',
    });
  }
}
