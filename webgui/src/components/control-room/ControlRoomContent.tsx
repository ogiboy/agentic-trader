import type { ReactNode } from 'react';

import {
  ControlRoomLoadingPanel,
  ControlRoomUnavailablePanel,
} from './LoadingPanel';

type ControlRoomContentProps = {
  activeView: ReactNode;
  dashboardAvailable: boolean;
  loading: boolean;
  loadingSeconds: number;
};

export function ControlRoomContent({
  activeView,
  dashboardAvailable,
  loading,
  loadingSeconds,
}: ControlRoomContentProps) {
  if (loading) {
    return <ControlRoomLoadingPanel loadingSeconds={loadingSeconds} />;
  }
  if (dashboardAvailable) {
    return activeView;
  }
  return <ControlRoomUnavailablePanel />;
}
