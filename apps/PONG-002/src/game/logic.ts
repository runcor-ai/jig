import {
  AI_REFRESH, BALL_RADIUS, BASE_SPEED, HEIGHT, LEFT_PADDLE_X, MAX_BOUNCE_ANGLE,
  MAX_DT, MAX_SERVE_ANGLE, MAX_SPEED, PADDLE_H, PADDLE_W, PLAYER_SPEED,
  RIGHT_PADDLE_X, SERVE_DELAY, SPEEDUP, WIDTH, WIN_SCORE,
} from './constants'
import { aiInput, aiTargetFor } from './ai'
import type { GameState, Input } from './types'

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))

export function initialState(): GameState {
  return {
    width: WIDTH,
    height: HEIGHT,
    playerY: (HEIGHT - PADDLE_H) / 2,
    computerY: (HEIGHT - PADDLE_H) / 2,
    ball: { x: WIDTH / 2, y: HEIGHT / 2, vx: BASE_SPEED, vy: 0 },
    playerScore: 0,
    computerScore: 0,
    phase: 'ready',
    winner: null,
    serveDelay: 0,
    aiTargetY: HEIGHT / 2,
    aiTimer: 0,
  }
}

export function restart(): GameState {
  return initialState()
}

/** Space: ready->playing, playing->paused, paused->playing, won->unchanged. */
export function toggleSpace(s: GameState): GameState {
  switch (s.phase) {
    case 'ready':
    case 'paused':
      return { ...s, phase: 'playing' }
    case 'playing':
      return { ...s, phase: 'paused' }
    default:
      return s
  }
}

/** Outgoing angle (radians) for a hit offset in [-1, 1]. */
export function hitAngle(offset: number): number {
  return clamp(offset, -1, 1) * MAX_BOUNCE_ANGLE
}

/** A fresh serve from the centre at base speed. dir: -1 toward the player, +1 toward the computer. */
export function serve(dir: 1 | -1, rng: () => number): GameState['ball'] {
  const angle = (rng() * 2 - 1) * MAX_SERVE_ANGLE
  return {
    x: WIDTH / 2,
    y: HEIGHT / 2,
    vx: dir * BASE_SPEED * Math.cos(angle),
    vy: BASE_SPEED * Math.sin(angle),
  }
}

export function step(
  s: GameState,
  input: Input,
  dt: number,
  rng: () => number = Math.random,
): GameState {
  if (s.phase !== 'playing') return { ...s, ball: { ...s.ball } }
  const d = clamp(dt, 0, MAX_DT)

  const playerY = clamp(s.playerY + input * PLAYER_SPEED * d, 0, s.height - PADDLE_H)

  // AI: target refreshed only every AI_REFRESH seconds of simulated time
  let aiTimer = s.aiTimer + d
  let aiTargetY = s.aiTargetY
  if (aiTimer >= AI_REFRESH - 1e-9) {
    aiTargetY = aiTargetFor(s.ball, s.height)
    aiTimer = 0
  }
  const computerY = clamp(
    s.computerY + aiInput(s.computerY, aiTargetY) * d,
    0,
    s.height - PADDLE_H,
  )

  const base: GameState = { ...s, playerY, computerY, aiTimer, aiTargetY }

  if (s.serveDelay > 0) {
    return { ...base, serveDelay: Math.max(0, s.serveDelay - d), ball: { ...s.ball } }
  }

  const R = BALL_RADIUS
  const { x, y } = s.ball
  let { vx, vy } = s.ball
  const nx = x + vx * d
  let ny = y + vy * d

  // paddle hit (swept on the x axis)
  const leftFace = LEFT_PADDLE_X + PADDLE_W
  const rightFace = RIGHT_PADDLE_X
  let hit: 'left' | 'right' | null = null
  let yAt = ny
  if (vx < 0 && x - R >= leftFace && nx - R <= leftFace) {
    const t = (x - R - leftFace) / ((x - R) - (nx - R) || 1)
    yAt = y + (ny - y) * t
    if (yAt + R >= playerY && yAt - R <= playerY + PADDLE_H) hit = 'left'
  } else if (vx > 0 && x + R <= rightFace && nx + R >= rightFace) {
    const t = (rightFace - (x + R)) / ((nx + R) - (x + R) || 1)
    yAt = y + (ny - y) * t
    if (yAt + R >= computerY && yAt - R <= computerY + PADDLE_H) hit = 'right'
  }

  if (hit) {
    const padY = hit === 'left' ? playerY : computerY
    const offset = (yAt - (padY + PADDLE_H / 2)) / (PADDLE_H / 2)
    const speed = Math.min(Math.hypot(vx, vy) * SPEEDUP, MAX_SPEED)
    const angle = hitAngle(offset)
    const dir = hit === 'left' ? 1 : -1
    return {
      ...base,
      ball: {
        x: hit === 'left' ? leftFace + R : rightFace - R,
        y: clamp(yAt, R, s.height - R),
        vx: dir * speed * Math.cos(angle),
        vy: speed * Math.sin(angle),
      },
    }
  }

  // walls
  if (ny <= R) {
    ny = R
    vy = Math.abs(vy)
  } else if (ny >= s.height - R) {
    ny = s.height - R
    vy = -Math.abs(vy)
  }

  // scoring
  if (nx < 0 || nx > s.width) {
    const playerScored = nx > s.width
    const playerScore = s.playerScore + (playerScored ? 1 : 0)
    const computerScore = s.computerScore + (playerScored ? 0 : 1)
    const won = playerScore >= WIN_SCORE || computerScore >= WIN_SCORE
    return {
      ...base,
      playerScore,
      computerScore,
      phase: won ? 'won' : 'playing',
      winner: won ? (playerScore >= WIN_SCORE ? 'player' : 'computer') : null,
      serveDelay: SERVE_DELAY,
      // serve toward the player who just lost the point
      ball: serve(playerScored ? 1 : -1, rng),
    }
  }

  return { ...base, ball: { x: nx, y: ny, vx, vy } }
}
