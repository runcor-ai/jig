import { useEffect, useRef } from 'react';
import { MAX_DT } from '../game/constants';

/** Runs onTick(dt) each animation frame while active; dt is clamped to MAX_DT. */
export function useGameLoop(onTick: (dt: number) => void, active: boolean): void {
  const tickRef = useRef(onTick);
  tickRef.current = onTick;

  useEffect(() => {
    if (!active) return;
    let last: number | null = null;
    let id = 0;
    const frame = (time: number) => {
      if (last !== null) {
        const dt = Math.min(Math.max((time - last) / 1000, 0), MAX_DT);
        tickRef.current(dt);
      }
      last = time;
      id = requestAnimationFrame(frame);
    };
    id = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(id);
  }, [active]);
}
