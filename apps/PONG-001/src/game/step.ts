import {
  BALL_SIZE,
  FIELD_HEIGHT,
  FIELD_WIDTH,
  LEFT_PADDLE_X,
  MAX_BALL_SPEED,
  MAX_BOUNCE_ANGLE,
  PADDLE_HEIGHT,
  PADDLE_WIDTH,
  PLAYER_SPEED,
  RIGHT_PADDLE_X,
  SPEED_UP,
  WIN_SCORE,
} from './constants';
import { updateAI } from './ai';
import { resetBall } from './state';
import type { GameState, Input, Serve } from './types';

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

function bounce(
  vx: number,
  vy: number,
  hitY: number,
  paddleY: number,
  dirX: 1 | -1,
): { vx: number; vy: number } {
  const speed = Math.min(Math.hypot(vx, vy) * SPEED_UP, MAX_BALL_SPEED);
  const offset = clamp(
    (hitY + BALL_SIZE / 2 - (paddleY + PADDLE_HEIGHT / 2)) / (PADDLE_HEIGHT / 2),
    -1,
    1,
  );
  const angle = offset * MAX_BOUNCE_ANGLE;
  return { vx: dirX * speed * Math.cos(angle), vy: speed * Math.sin(angle) };
}

/** Pure step. No randomness or clock access: serve is injected. */
export function step(
  state: GameState,
  input: Input,
  dt: number,
  serve: Serve = { angle: 0 },
): GameState {
  if (state.phase !== 'playing') return state;

  const dir = (input.down ? 1 : 0) - (input.up ? 1 : 0);
  const playerY = clamp(state.player.y + dir * PLAYER_SPEED * dt, 0, FIELD_HEIGHT - PADDLE_HEIGHT);
  const ai = updateAI(state.ai, state.ball.y + BALL_SIZE / 2, dt);

  const px = state.ball.x;
  const py = state.ball.y;
  let { vx, vy } = state.ball;
  let x = px + vx * dt;
  let y = py + vy * dt;

  // Wall bounces
  if (y <= 0) {
    y = -y;
    vy = Math.abs(vy);
  } else if (y + BALL_SIZE >= FIELD_HEIGHT) {
    y = 2 * (FIELD_HEIGHT - BALL_SIZE) - y;
    vy = -Math.abs(vy);
  }
  y = clamp(y, 0, FIELD_HEIGHT - BALL_SIZE);

  // Paddle collisions (swept along x so fast balls cannot tunnel)
  const leftEdge = LEFT_PADDLE_X + PADDLE_WIDTH;
  if (vx < 0 && x <= leftEdge && px + BALL_SIZE > LEFT_PADDLE_X) {
    const t = px > x ? clamp((px - leftEdge) / (px - x), 0, 1) : 1;
    const hitY = clamp(py + (y - py) * t, 0, FIELD_HEIGHT - BALL_SIZE);
    if (hitY + BALL_SIZE > playerY && hitY < playerY + PADDLE_HEIGHT) {
      ({ vx, vy } = bounce(vx, vy, hitY, playerY, 1));
      x = leftEdge;
      y = hitY;
    }
  } else if (vx > 0 && x + BALL_SIZE >= RIGHT_PADDLE_X && px < RIGHT_PADDLE_X + PADDLE_WIDTH) {
    const target = RIGHT_PADDLE_X - BALL_SIZE;
    const t = x > px ? clamp((target - px) / (x - px), 0, 1) : 1;
    const hitY = clamp(py + (y - py) * t, 0, FIELD_HEIGHT - BALL_SIZE);
    if (hitY + BALL_SIZE > ai.y && hitY < ai.y + PADDLE_HEIGHT) {
      ({ vx, vy } = bounce(vx, vy, hitY, ai.y, -1));
      x = target;
      y = hitY;
    }
  }

  let { playerScore, computerScore } = state;
  let ball = { x, y, vx, vy };
  let scored: 'player' | 'computer' | null = null;
  if (x + BALL_SIZE < 0) scored = 'computer';
  else if (x > FIELD_WIDTH) scored = 'player';

  let phase: GameState['phase'] = state.phase;
  let winner = state.winner;
  if (scored === 'player') playerScore += 1;
  if (scored === 'computer') computerScore += 1;
  if (scored) {
    // serve toward the side that conceded unless a direction is injected
    const d = serve.dir ?? (scored === 'player' ? 1 : -1);
    ball = resetBall(d, serve.angle);
    if (playerScore >= WIN_SCORE) {
      phase = 'gameover';
      winner = 'player';
    } else if (computerScore >= WIN_SCORE) {
      phase = 'gameover';
      winner = 'computer';
    }
  }

  return { ...state, phase, winner, playerScore, computerScore, player: { y: playerY }, ai, ball };
}
