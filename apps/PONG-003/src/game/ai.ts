import { AI_DEAD_ZONE, AI_DELAY } from './constants';
import type { Sample } from './state';

/** -1 (up), 0 (stay) or +1 (down) toward the target; 0 inside the dead zone. */
export function aiDirection(paddleCenterY: number, targetY: number): -1 | 0 | 1 {
  const diff = targetY - paddleCenterY;
  if (Math.abs(diff) <= AI_DEAD_ZONE) return 0;
  return diff < 0 ? -1 : 1;
}

/** The ball y as it was AI_DELAY seconds before `now` (oldest sample if history is shorter). */
export function aiTarget(history: Sample[], now: number): number {
  const cutoff = now - AI_DELAY;
  let chosen = history[0];
  for (const s of history) {
    if (s.t <= cutoff) chosen = s;
    else break;
  }
  return chosen.y;
}

/** Append a sample and drop samples that can no longer be the delayed target. */
export function recordSample(history: Sample[], t: number, y: number): Sample[] {
  const next = [...history, { t, y }];
  const cutoff = t - AI_DELAY;
  while (next.length > 1 && next[1].t <= cutoff) next.shift();
  return next;
}
