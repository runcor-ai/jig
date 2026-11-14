import {
  BALL_MAX_SPEED,
  BALL_SIZE,
  BALL_START_SPEED,
  HEIGHT,
  LEFT_PADDLE_X,
  MAX_VY,
  PADDLE_H,
  PADDLE_W,
  PLAYER_SPEED,
  RIGHT_PADDLE_X,
  SPEEDUP,
  WIDTH,
  WIN_SCORE,
} from './config';
import { computeAiMove } from './ai';

export type Status = 'playing' | 'paused' | 'gameover';
export type Winner = 'player' | 'computer' | null;

export interface Ball {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

export interface GameState {
  leftY: number;
  rightY: number;
  ball: Ball;
  playerScore: number;
  computerScore: number;
  status: Status;
  winner: Winner;
}

export interface Input {
  /** -1 up, 0 none, 1 down */
  dir: -1 | 0 | 1;
}

export const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

/** direction: -1 serves toward the left (player), 1 toward the right (computer). */
export function resetBall(direction: -1 | 1, vy = 0): Ball {
  return {
    x: (WIDTH - BALL_SIZE) / 2,
    y: (HEIGHT - BALL_SIZE) / 2,
    vx: direction * BALL_START_SPEED,
    vy,
  };
}

export function createInitialState(serveDirection: -1 | 1 = -1): GameState {
  return {
    leftY: (HEIGHT - PADDLE_H) / 2,
    rightY: (HEIGHT - PADDLE_H) / 2,
    ball: resetBall(serveDirection),
    playerScore: 0,
    computerScore: 0,
    status: 'playing',
    winner: null,
  };
}

export function capSpeed(ball: Ball): Ball {
  const speed = Math.hypot(ball.vx, ball.vy);
  if (speed <= BALL_MAX_SPEED) return ball;
  const k = BALL_MAX_SPEED / speed;
  return { ...ball, vx: ball.vx * k, vy: ball.vy * k };
}

function overlapsY(ball: Ball, paddleY: number) {
  return ball.y + BALL_SIZE >= paddleY && ball.y <= paddleY + PADDLE_H;
}

function hitVy(ball: Ball, paddleY: number) {
  const offset = (ball.y + BALL_SIZE / 2 - (paddleY + PADDLE_H / 2)) / (PADDLE_H / 2);
  return clamp(offset, -1, 1) * MAX_VY;
}

/**
 * Advance the game by dt seconds. Pure: returns a new state.
 * `rng` only picks the vertical serve speed after a point.
 */
export function step(
  state: GameState,
  input: Input,
  dt: number,
  rng: () => number = Math.random,
): GameState {
  if (state.status !== 'playing') return state;

  const leftY = clamp(state.leftY + input.dir * PLAYER_SPEED * dt, 0, HEIGHT - PADDLE_H);
  const rightY = computeAiMove(state, dt);

  let ball: Ball = {
    ...state.ball,
    x: state.ball.x + state.ball.vx * dt,
    y: state.ball.y + state.ball.vy * dt,
  };

  // walls
  if (ball.y <= 0) ball = { ...ball, y: 0, vy: Math.abs(ball.vy) };
  else if (ball.y >= HEIGHT - BALL_SIZE) ball = { ...ball, y: HEIGHT - BALL_SIZE, vy: -Math.abs(ball.vy) };

  // paddles
  if (
    ball.vx < 0 &&
    ball.x <= LEFT_PADDLE_X + PADDLE_W &&
    ball.x + BALL_SIZE >= LEFT_PADDLE_X &&
    overlapsY(ball, leftY)
  ) {
    ball = capSpeed({ ...ball, x: LEFT_PADDLE_X + PADDLE_W, vx: Math.abs(ball.vx) * SPEEDUP, vy: hitVy(ball, leftY) });
  } else if (
    ball.vx > 0 &&
    ball.x + BALL_SIZE >= RIGHT_PADDLE_X &&
    ball.x <= RIGHT_PADDLE_X + PADDLE_W &&
    overlapsY(ball, rightY)
  ) {
    ball = capSpeed({
      ...ball,
      x: RIGHT_PADDLE_X - BALL_SIZE,
      vx: -Math.abs(ball.vx) * SPEEDUP,
      vy: hitVy(ball, rightY),
    });
  }

  let { playerScore, computerScore } = state;
  let scored: 'player' | 'computer' | null = null;
  if (ball.x < -BALL_SIZE) scored = 'computer';
  else if (ball.x > WIDTH) scored = 'player';

  if (scored === 'computer') {
    computerScore += 1;
    ball = resetBall(-1, (rng() - 0.5) * 200); // serve toward the player (who conceded)
  } else if (scored === 'player') {
    playerScore += 1;
    ball = resetBall(1, (rng() - 0.5) * 200); // serve toward the computer
  }

  let status: Status = state.status;
  let winner: Winner = null;
  if (playerScore >= WIN_SCORE) {
    status = 'gameover';
    winner = 'player';
  } else if (computerScore >= WIN_SCORE) {
    status = 'gameover';
    winner = 'computer';
  }

  return { leftY, rightY, ball, playerScore, computerScore, status, winner };
}
