import { useEffect } from 'react';
import type { Action, Status } from '../game/game';
import { gravityMs } from '../game/scoring';

/** Dispatches 'tick' every gravityMs(level) while playing. `resetToken` restarts the timer when it changes. */
export function useGravity(
  status: Status,
  level: number,
  dispatch: (a: Action) => void,
  resetToken: number = 0,
): void {
  useEffect(() => {
    if (status !== 'playing') return;
    const id = setInterval(() => dispatch('tick'), gravityMs(level));
    return () => clearInterval(id);
  }, [status, level, dispatch, resetToken]);
}
