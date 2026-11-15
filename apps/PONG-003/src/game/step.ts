import { aiDirection, aiTarget, recordSample } from './ai';
import {
  AI_SPEED,
  HEIGHT,
  MAX_BALL_SPEED,
  MAX_BOUNCE_ANGLE,
  PLAYER_SPEED,
  SERVE_DELAY,
  SPEEDUP,
  SUBSTEP,
  WIDTH,
  WIN_SCORE,
} from './constants';
import { serveBall, type Ball, type GameState, type Input, type Paddle, type Rng, type Side } from './state';

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const clampPaddle = (p: Paddle, y: number): Paddle => ({ ...p, y: clamp(y, 0, HEIGHT - p.height) });
const centerY = (r: { y: number; height: number }) => r.y + r.height / 2;

function overlaps(b: Ball, p: Paddle): boolean {
  return b.x < p.x + p.width && b.x + b.width > p.x && b.y < p.y + p.height && b.y + b.height > p.y;
}

function bounceOff(ball: Ball, paddle: Paddle, dirX: 1 | -1): Ball {
  const speed = Math.hypot(ball.vx, ball.vy);
  const offset = clamp((centerY(ball) - centerY(paddle)) / (paddle.height / 2), -1, 1);
  const angle = offset * MAX_BOUNCE_ANGLE;
  const next = Math.min(MAX_BALL_SPEED, speed * SPEEDUP);
  return {
    ...ball,
    x: dirX === 1 ? paddle.x + paddle.width : paddle.x - ball.width,
    vx: dirX * next * Math.cos(angle),
    vy: next * Math.sin(angle),
  };
}

function scorePoint(s: GameState, scorer: Side, rng: Rng): GameState {
  const scores = { ...s.scores, [scorer]: s.scores[scorer] + 1 };
  if (scores[scorer] >= WIN_SCORE) {
    const still = { ...serveBall(rng, 1), vx: 0, vy: 0 };
    return { ...s, scores, phase: 'over', winner: scorer, ball: still };
  }
  // Serve toward the side that conceded: player scored -> computer (right) concedes.
  const ball = serveBall(rng, scorer === 'player' ? 1 : -1);
  return {
    ...s,
    scores,
    ball,
    phase: 'serving',
    serveTimer: SERVE_DELAY,
    aiHistory: [{ t: s.time, y: centerY(ball) }],
  };
}

function movePaddles(s: GameState, input: Input, h: number, target: number): GameState {
  const dir = (input.down ? 1 : 0) - (input.up ? 1 : 0);
  return {
    ...s,
    left: clampPaddle(s.left, s.left.y + dir * PLAYER_SPEED * h),
    right: clampPaddle(s.right, s.right.y + aiDirection(centerY(s.right), target) * AI_SPEED * h),
  };
}

function substep(state: GameState, input: Input, h: number, target: number, rng: Rng): GameState {
  const s = movePaddles(state, input, h, target);
  let ball: Ball = { ...s.ball, x: s.ball.x + s.ball.vx * h, y: s.ball.y + s.ball.vy * h };

  if (ball.y < 0) ball = { ...ball, y: 0, vy: Math.abs(ball.vy) };
  else if (ball.y + ball.height > HEIGHT) ball = { ...ball, y: HEIGHT - ball.height, vy: -Math.abs(ball.vy) };

  // Only bounce when moving toward the paddle and the ball has not already passed its centre line.
  if (ball.vx < 0 && overlaps(ball, s.left) && ball.x + ball.width / 2 >= s.left.x + s.left.width / 2) {
    ball = bounceOff(ball, s.left, 1);
  } else if (ball.vx > 0 && overlaps(ball, s.right) && ball.x + ball.width / 2 <= s.right.x + s.right.width / 2) {
    ball = bounceOff(ball, s.right, -1);
  }

  const next = { ...s, ball };
  if (ball.x + ball.width < 0) return scorePoint(next, 'computer', rng);
  if (ball.x > WIDTH) return scorePoint(next, 'player', rng);
  return next;
}

/** Pure game step. Does nothing in 'ready', 'paused' and 'over'. */
export function step(state: GameState, input: Input, dt: number, rng: Rng): GameState {
  if (state.phase === 'ready' || state.phase === 'paused' || state.phase === 'over' || !(dt > 0)) {
    return state;
  }
  const time = state.time + dt;
  const target = aiTarget(state.aiHistory, time);

  if (state.phase === 'serving') {
    const moved = movePaddles({ ...state, time }, input, dt, target);
    const serveTimer = state.serveTimer - dt;
    if (serveTimer <= 1e-9) {
      return { ...moved, phase: 'playing', serveTimer: 0, aiHistory: [{ t: time, y: centerY(moved.ball) }] };
    }
    return { ...moved, serveTimer };
  }

  // Sub-step so a fast ball cannot tunnel through a paddle.
  const n = Math.ceil(dt / SUBSTEP);
  const h = dt / n;
  let s: GameState = { ...state, time };
  for (let i = 0; i < n && s.phase === 'playing'; i++) s = substep(s, input, h, target, rng);
  if (s.phase === 'playing') s = { ...s, aiHistory: recordSample(s.aiHistory, time, centerY(s.ball)) };
  return s;
}
