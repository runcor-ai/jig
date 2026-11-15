import { useEffect, useRef } from 'react';
import { MAX_DT } from '../game/constants';

export const clampDt = (dt: number) => Math.min(Math.max(dt, 0), MAX_DT);

/** requestAnimationFrame loop; calls onFrame(dt seconds, clamped to 0.05). Cancelled on unmount. */
export function useGameLoop(onFrame: (dt: number) => void) {
  const cbRef = useRef(onFrame);
  cbRef.current = onFrame;

  useEffect(() => {
    let id = 0;
    let last: number | null = null;
    const frame = (ts: number) => {
      if (last !== null) cbRef.current(clampDt((ts - last) / 1000));
      last = ts;
      id = requestAnimationFrame(frame);
    };
    id = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(id);
  }, []);
}
