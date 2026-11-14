export const FIELD_W = 800;
export const FIELD_H = 500;
export const PADDLE_W = 12;
export const PADDLE_H = 90;
export const PADDLE_MARGIN = 20;
export const BALL_SIZE = 12;
export const PLAYER_SPEED = 420;
export const BALL_BASE_SPEED = 360;
export const MAX_BALL_SPEED = 720;
export const BALL_SPEEDUP = 1.06;
export const MAX_BOUNCE_ANGLE = Math.PI / 3; // 60 degrees
export const AI_SPEED = 260;
export const AI_DEAD_ZONE = 10;
export const WIN_SCORE = 10;

export const PLAYER_X = PADDLE_MARGIN;
export const AI_X = FIELD_W - PADDLE_MARGIN - PADDLE_W;
export const MAX_PADDLE_Y = FIELD_H - PADDLE_H;
export const MAX_BALL_Y = FIELD_H - BALL_SIZE;

export type Status = 'ready' | 'playing' | 'paused' | 'over';
export type Winner = 'player' | 'computer' | null;

export interface Ball {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

export interface GameState {
  status: Status;
  playerY: number;
  aiY: number;
  ball: Ball;
  playerScore: number;
  aiScore: number;
  serveDirection: -1 | 1;
  winner: Winner;
}

export interface Input {
  up: boolean;
  down: boolean;
}

export const clamp = (v: number, lo: number, hi: number): number =>
  Number.isFinite(v) ? Math.min(hi, Math.max(lo, v)) : lo;

/** Validates configuration constants; throws if inconsistent. */
export function validateConfig(): void {
  const positives = [FIELD_W, FIELD_H, PADDLE_W, PADDLE_H, BALL_SIZE, PLAYER_SPEED,
    BALL_BASE_SPEED, MAX_BALL_SPEED, AI_SPEED, WIN_SCORE];
  if (!positives.every((n) => Number.isFinite(n) && n > 0)) throw new Error('Invalid config: non-positive value');
  if (BALL_BASE_SPEED > MAX_BALL_SPEED) throw new Error('Invalid config: base speed exceeds max');
  if (AI_SPEED >= MAX_BALL_SPEED * Math.sin(MAX_BOUNCE_ANGLE)) throw new Error('Invalid config: AI too fast');
  if (PADDLE_H >= FIELD_H) throw new Error('Invalid config: paddle too tall');
}
validateConfig();
