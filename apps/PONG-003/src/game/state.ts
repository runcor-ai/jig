import {
  BALL_SIZE,
  HEIGHT,
  INITIAL_BALL_SPEED,
  PADDLE_HEIGHT,
  PADDLE_MARGIN,
  PADDLE_WIDTH,
  SERVE_MAX_ANGLE,
  WIDTH,
} from './constants';

export type Phase = 'ready' | 'playing' | 'paused' | 'serving' | 'over';
export type Side = 'player' | 'computer';
export type Rng = () => number;

export interface Input {
  up: boolean;
  down: boolean;
}

export interface Paddle {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Ball {
  x: number;
  y: number;
  width: number;
  height: number;
  vx: number;
  vy: number;
}

export interface Sample {
  t: number;
  y: number;
}

export interface GameState {
  phase: Phase;
  left: Paddle; // player
  right: Paddle; // computer
  ball: Ball;
  scores: { player: number; computer: number };
  winner: Side | null;
  serveTimer: number; // seconds left in 'serving'
  time: number; // simulated seconds while the game ran
  aiHistory: Sample[]; // ball centre y samples, for the AI reaction delay
}

export const NO_INPUT: Input = { up: false, down: false };

/** A centred ball launched in direction dir (-1 = left, +1 = right) at a random angle within +-30 degrees. */
export function serveBall(rng: Rng, dir: 1 | -1): Ball {
  const angle = (rng() * 2 - 1) * SERVE_MAX_ANGLE;
  return {
    x: (WIDTH - BALL_SIZE) / 2,
    y: (HEIGHT - BALL_SIZE) / 2,
    width: BALL_SIZE,
    height: BALL_SIZE,
    vx: dir * INITIAL_BALL_SPEED * Math.cos(angle),
    vy: INITIAL_BALL_SPEED * Math.sin(angle),
  };
}

/** Fresh game in phase 'ready'. The first serve goes toward the player (left). */
export function createInitialState(rng: Rng = () => 0.5): GameState {
  const ball = serveBall(rng, -1);
  const y = (HEIGHT - PADDLE_HEIGHT) / 2;
  return {
    phase: 'ready',
    left: { x: PADDLE_MARGIN, y, width: PADDLE_WIDTH, height: PADDLE_HEIGHT },
    right: { x: WIDTH - PADDLE_MARGIN - PADDLE_WIDTH, y, width: PADDLE_WIDTH, height: PADDLE_HEIGHT },
    ball,
    scores: { player: 0, computer: 0 },
    winner: null,
    serveTimer: 0,
    time: 0,
    aiHistory: [{ t: 0, y: ball.y + ball.height / 2 }],
  };
}
