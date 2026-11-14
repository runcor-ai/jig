import { useEffect, useRef } from 'react';
import { DT_CAP_MS } from '../game/config';

/**
 * requestAnimationFrame loop. Calls tick(dtSeconds) once per frame while active,
 * with dt clamped to DT_CAP_MS. Cancels the pending frame on unmount/deactivate.
 */
export function useGameLoop(tick: (dtSeconds: number) => void, active: boolean) {
  const tickRef = useRef(tick);
  tickRef.current = tick;

  useEffect(() => {
    if (!active) return;
    let last: number | null = null;
    let id = 0;
    const frame = (now: number) => {
      const dtMs = last === null ? 0 : Math.min(Math.max(now - last, 0), DT_CAP_MS);
      last = now;
      tickRef.current(dtMs / 1000);
      id = requestAnimationFrame(frame);
    };
    id = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(id);
  }, [active]);
}
