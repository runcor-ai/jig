import { AI_DEAD_ZONE, AI_SPEED, BALL_SIZE, HEIGHT, PADDLE_H } from './config';
import type { GameState } from './logic';

/** Returns the computer paddle's new y after dt seconds. */
export function computeAiMove(state: GameState, dt: number): number {
  const ballCenter = state.ball.y + BALL_SIZE / 2;
  const paddleCenter = state.rightY + PADDLE_H / 2;
  const diff = ballCenter - paddleCenter;
  if (Math.abs(diff) <= AI_DEAD_ZONE) return state.rightY;
  const move = Math.min(Math.abs(diff), AI_SPEED * dt) * Math.sign(diff);
  return Math.min(HEIGHT - PADDLE_H, Math.max(0, state.rightY + move));
}
