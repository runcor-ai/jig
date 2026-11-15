import { AI_DEAD_ZONE, AI_SPEED, HEIGHT, PADDLE_H } from './constants'
import type { Ball } from './types'

/** Where the AI wants its paddle centre: the ball's y if it approaches, else the centre. */
export function aiTargetFor(ball: Ball, height: number = HEIGHT): number {
  return ball.vx > 0 ? ball.y : height / 2
}

/**
 * Desired paddle velocity in units/s (never beyond +-AI_SPEED).
 * Zero inside the dead zone.
 */
export function aiInput(paddleY: number, targetY: number): number {
  const diff = targetY - (paddleY + PADDLE_H / 2)
  if (Math.abs(diff) <= AI_DEAD_ZONE) return 0
  return diff > 0 ? AI_SPEED : -AI_SPEED
}
