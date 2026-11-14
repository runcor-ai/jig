import {
  AI_X, BALL_BASE_SPEED, BALL_SIZE, BALL_SPEEDUP, FIELD_H, FIELD_W, MAX_BALL_SPEED, MAX_BALL_Y,
  MAX_BOUNCE_ANGLE, MAX_PADDLE_Y, PADDLE_H, PADDLE_W, PLAYER_SPEED, PLAYER_X, WIN_SCORE, clamp,
  type Ball, type GameState, type Input,
} from './config';
import { moveAi } from './ai';

function serveBall(direction: -1 | 1, pointsPlayed: number): Ball {
  const vyDir = pointsPlayed % 2 === 0 ? 1 : -1;
  return {
    x: (FIELD_W - BALL_SIZE) / 2,
    y: (FIELD_H - BALL_SIZE) / 2,
    vx: direction * BALL_BASE_SPEED * 0.95,
    vy: vyDir * BALL_BASE_SPEED * 0.3,
  };
}

export function createInitialState(): GameState {
  return {
    status: 'ready',
    playerY: MAX_PADDLE_Y / 2,
    aiY: MAX_PADDLE_Y / 2,
    ball: serveBall(-1, 0),
    playerScore: 0,
    aiScore: 0,
    serveDirection: -1,
    winner: null,
  };
}

/** Space: start from ready, toggle pause/resume while playing. No effect when over. */
export function startOrTogglePause(s: GameState): GameState {
  if (s.status === 'ready' || s.status === 'paused') return { ...s, status: 'playing' };
  if (s.status === 'playing') return { ...s, status: 'paused' };
  return s;
}

/** Pause only if currently playing (used for hidden tab). */
export function pause(s: GameState): GameState {
  return s.status === 'playing' ? { ...s, status: 'paused' } : s;
}

/** Restart: fresh game, immediately playing. */
export function restart(): GameState {
  return { ...createInitialState(), status: 'playing' };
}

function limitSpeed(vx: number, vy: number): { vx: number; vy: number } {
  const sp = Math.hypot(vx, vy);
  if (sp > MAX_BALL_SPEED) {
    const k = MAX_BALL_SPEED / sp;
    return { vx: vx * k, vy: vy * k };
  }
  return { vx, vy };
}

function paddleBounce(ball: Ball, paddleY: number, dir: 1 | -1): Ball {
  const rel = clamp(((ball.y + BALL_SIZE / 2) - (paddleY + PADDLE_H / 2)) / (PADDLE_H / 2), -1, 1);
  const angle = rel * MAX_BOUNCE_ANGLE;
  const speed = Math.min(Math.hypot(ball.vx, ball.vy) * BALL_SPEEDUP, MAX_BALL_SPEED);
  return { ...ball, vx: dir * speed * Math.cos(angle), vy: speed * Math.sin(angle) };
}

function score(s: GameState, who: 'player' | 'computer'): GameState {
  const playerScore = Math.min(WIN_SCORE, s.playerScore + (who === 'player' ? 1 : 0));
  const aiScore = Math.min(WIN_SCORE, s.aiScore + (who === 'computer' ? 1 : 0));
  const serveDirection: -1 | 1 = s.serveDirection === -1 ? 1 : -1;
  const next: GameState = {
    ...s, playerScore, aiScore, serveDirection,
    ball: serveBall(serveDirection, playerScore + aiScore),
  };
  if (playerScore >= WIN_SCORE) return { ...next, status: 'over', winner: 'player' };
  if (aiScore >= WIN_SCORE) return { ...next, status: 'over', winner: 'computer' };
  return next;
}

/** Advance the game by dt seconds. Only advances while status is 'playing'. */
export function step(s: GameState, input: Input, dt: number): GameState {
  if (s.status !== 'playing' || !(dt > 0)) return s;
  dt = Math.min(dt, 0.05);

  const dir = (input.down ? 1 : 0) - (input.up ? 1 : 0);
  const playerY = clamp(s.playerY + dir * PLAYER_SPEED * dt, 0, MAX_PADDLE_Y);
  const aiY = moveAi(s.aiY, s.ball.y, dt);

  let ball: Ball = { ...s.ball, x: s.ball.x + s.ball.vx * dt, y: s.ball.y + s.ball.vy * dt };

  if (ball.y <= 0) ball = { ...ball, y: 0, vy: Math.abs(ball.vy) };
  else if (ball.y >= MAX_BALL_Y) ball = { ...ball, y: MAX_BALL_Y, vy: -Math.abs(ball.vy) };

  const overlapsY = (py: number) => ball.y + BALL_SIZE > py && ball.y < py + PADDLE_H;
  if (ball.vx < 0 && ball.x <= PLAYER_X + PADDLE_W && ball.x + BALL_SIZE >= PLAYER_X && overlapsY(playerY)) {
    ball = paddleBounce({ ...ball, x: PLAYER_X + PADDLE_W }, playerY, 1);
  } else if (ball.vx > 0 && ball.x + BALL_SIZE >= AI_X && ball.x <= AI_X + PADDLE_W && overlapsY(aiY)) {
    ball = paddleBounce({ ...ball, x: AI_X - BALL_SIZE }, aiY, -1);
  }
  ball = { ...ball, ...limitSpeed(ball.vx, ball.vy) };

  const moved: GameState = { ...s, playerY, aiY, ball };
  if (ball.x + BALL_SIZE < 0) return score(moved, 'computer');
  if (ball.x > FIELD_W) return score(moved, 'player');
  return moved;
}
