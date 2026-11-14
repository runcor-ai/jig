import { AI_DEAD_ZONE, AI_SPEED, MAX_PADDLE_Y, PADDLE_H, BALL_SIZE, clamp } from './config';

/** Returns the new computer paddle y, moving toward ballY at a capped speed. */
export function moveAi(aiY: number, ballY: number, dt: number): number {
  const target = ballY + BALL_SIZE / 2 - PADDLE_H / 2;
  const diff = target - aiY;
  if (Math.abs(diff) <= AI_DEAD_ZONE) return clamp(aiY, 0, MAX_PADDLE_Y);
  const maxMove = AI_SPEED * dt;
  const move = Math.sign(diff) * Math.min(Math.abs(diff), maxMove);
  return clamp(aiY + move, 0, MAX_PADDLE_Y);
}
