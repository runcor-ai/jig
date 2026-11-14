import {
  AI_DEAD_ZONE,
  AI_MAX_SPEED,
  AI_REACTION_SECONDS,
  FIELD_HEIGHT,
  PADDLE_HEIGHT,
} from './constants';
import type { AIState } from './types';

/** Pure AI update. ballCenterY is only sampled when the reaction timer elapses. */
export function updateAI(ai: AIState, ballCenterY: number, dt: number): AIState {
  let timer = ai.timer + dt;
  let targetY = ai.targetY;
  if (timer >= AI_REACTION_SECONDS) {
    timer -= AI_REACTION_SECONDS;
    targetY = ballCenterY;
  }
  const centre = ai.y + PADDLE_HEIGHT / 2;
  const diff = targetY - centre;
  let y = ai.y;
  if (Math.abs(diff) > AI_DEAD_ZONE) {
    const maxMove = AI_MAX_SPEED * dt;
    y += Math.max(-maxMove, Math.min(maxMove, diff));
  }
  y = Math.max(0, Math.min(FIELD_HEIGHT - PADDLE_HEIGHT, y));
  return { y, targetY, timer };
}
