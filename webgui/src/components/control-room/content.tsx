import type { ReactNode } from 'react';

import type { ControlRoomCopy } from './copy/types';
import {
  ControlRoomLoadingPanel,
  ControlRoomUnavailablePanel,
} from './loading-panel';

type ControlRoomContentProps = {
  activeView: ReactNode;
  copy: ControlRoomCopy;
  dashboardAvailable: boolean;
  loading: boolean;
  loadingSeconds: number;
};

export function ControlRoomContent({
  activeView,
  copy,
  dashboardAvailable,
  loading,
  loadingSeconds,
}: ControlRoomContentProps) {
  if (loading) {
    return (
      <ControlRoomLoadingPanel copy={copy} loadingSeconds={loadingSeconds} />
    );
  }
  if (dashboardAvailable) {
    return activeView;
  }
  return <ControlRoomUnavailablePanel copy={copy} />;
}
