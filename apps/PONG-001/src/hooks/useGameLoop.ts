import { useEffect, useRef } from 'react';

export const FIXED_DT = 1 / 60;

/** Fixed-timestep rAF loop. Calls update(FIXED_DT) zero or more times per frame. */
export function useGameLoop(update: (dt: number) => void, onHidden: () => void) {
  const updateRef = useRef(update);
  const hiddenRef = useRef(onHidden);
  updateRef.current = update;
  hiddenRef.current = onHidden;

  useEffect(() => {
    let raf = 0;
    let last: number | null = null;
    let acc = 0;
    const frame = (t: number) => {
      if (last !== null) {
        acc += Math.min((t - last) / 1000, 0.25);
        while (acc >= FIXED_DT) {
          updateRef.current(FIXED_DT);
          acc -= FIXED_DT;
        }
      }
      last = t;
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    const vis = () => { if (document.hidden) { hiddenRef.current(); last = null; acc = 0; } };
    document.addEventListener('visibilitychange', vis);
    return () => {
      cancelAnimationFrame(raf);
      document.removeEventListener('visibilitychange', vis);
    };
  }, []);
}
