import { describe, expect, it } from 'vitest';
import {
  BALL_SIZE,
  BASE_BALL_SPEED,
  FIELD_HEIGHT,
  FIELD_WIDTH,
  MAX_BALL_SPEED,
  PADDLE_HEIGHT,
  PADDLE_WIDTH,
  PLAYER_SPEED,
  RIGHT_PADDLE_X,
  WIN_SCORE,
} from './constants';
import { applyCommand, createInitialState } from './state';
import { step } from './step';
import type { GameState, Input } from './types';

const none: Input = { up: false, down: false };
const playing = (over: Partial<GameState> = {}): GameState => ({
  ...createInitialState(),
  phase: 'playing',
  ...over,
});
const withBall = (ball: Partial<GameState['ball']>, over: Partial<GameState> = {}) => {
  const s = playing(over);
  return { ...s, ball: { ...s.ball, ...ball } };
};
const DT = 1 / 60;

describe('initial state (R-02)', () => {
  it('centres paddles and ball', () => {
    const s = createInitialState();
    expect(s.player.y).toBe((FIELD_HEIGHT - PADDLE_HEIGHT) / 2);
    expect(s.ai.y).toBe((FIELD_HEIGHT - PADDLE_HEIGHT) / 2);
    expect(s.ball.x + BALL_SIZE / 2).toBe(FIELD_WIDTH / 2);
    expect(s.ball.y + BALL_SIZE / 2).toBe(FIELD_HEIGHT / 2);
    expect(s.phase).toBe('ready');
  });
});

describe('player paddle (R-03)', () => {
  it('moves up and down by speed*dt', () => {
    const s = playing();
    expect(step(s, { up: true, down: false }, DT).player.y).toBeCloseTo(s.player.y - PLAYER_SPEED * DT);
    expect(step(s, { up: false, down: true }, DT).player.y).toBeCloseTo(s.player.y + PLAYER_SPEED * DT);
  });
  it('clamps to the field', () => {
    const top = playing({ player: { y: 1 } });
    expect(step(top, { up: true, down: false }, 0.03).player.y).toBe(0);
    const bot = playing({ player: { y: FIELD_HEIGHT - PADDLE_HEIGHT - 1 } });
    expect(step(bot, { up: false, down: true }, 0.03).player.y).toBe(FIELD_HEIGHT - PADDLE_HEIGHT);
  });
  it('cancels when both held', () => {
    const s = playing();
    expect(step(s, { up: true, down: true }, DT).player.y).toBe(s.player.y);
  });
});

describe('wall bounces (R-05)', () => {
  it('bounces off the top wall', () => {
    const s = withBall({ y: 1, vy: -300, vx: 200, x: 300 });
    const n = step(s, none, DT);
    expect(n.ball.vy).toBeGreaterThan(0);
    expect(n.ball.vx).toBe(200);
    expect(n.ball.y).toBeGreaterThanOrEqual(0);
  });
  it('bounces off the bottom wall', () => {
    const s = withBall({ y: FIELD_HEIGHT - BALL_SIZE - 1, vy: 300, vx: 200, x: 300 });
    const n = step(s, none, DT);
    expect(n.ball.vy).toBeLessThan(0);
    expect(n.ball.vx).toBe(200);
    expect(n.ball.y + BALL_SIZE).toBeLessThanOrEqual(FIELD_HEIGHT);
  });
  it('is pure/deterministic', () => {
    const s = withBall({ x: 300, vx: 100, vy: 50 });
    expect(step(s, none, DT)).toEqual(step(s, none, DT));
  });
});

describe('paddle bounce (R-06)', () => {
  const leftHit = (offsetFromCentre: number, speed = BASE_BALL_SPEED) => {
    const py = 200;
    const s = withBall(
      { x: PADDLE_WIDTH + 2, y: py + PADDLE_HEIGHT / 2 + offsetFromCentre - BALL_SIZE / 2, vx: -speed, vy: 0 },
      { player: { y: py } },
    );
    return { s, n: step(s, none, DT) };
  };
  it('centre hit: vy≈0, vx reversed', () => {
    const { n } = leftHit(0);
    expect(n.ball.vy).toBeCloseTo(0, 5);
    expect(n.ball.vx).toBeGreaterThan(0);
  });
  it('edge hits go up/down at no more than 60 degrees', () => {
    const up = leftHit(-PADDLE_HEIGHT / 2).n.ball;
    const down = leftHit(PADDLE_HEIGHT / 2).n.ball;
    expect(up.vy).toBeLessThan(0);
    expect(down.vy).toBeGreaterThan(0);
    for (const b of [up, down]) {
      expect(Math.abs(Math.atan2(b.vy, b.vx))).toBeLessThanOrEqual((60 * Math.PI) / 180 + 1e-9);
    }
  });
  it('speeds up by 1.05, capped', () => {
    const { n } = leftHit(10);
    expect(Math.hypot(n.ball.vx, n.ball.vy)).toBeCloseTo(BASE_BALL_SPEED * 1.05, 5);
    const fast = leftHit(10, MAX_BALL_SPEED - 5).n;
    expect(Math.hypot(fast.ball.vx, fast.ball.vy)).toBeCloseTo(MAX_BALL_SPEED, 5);
  });
  it('moves ball outside paddle so it cannot double hit', () => {
    const { n } = leftHit(0);
    expect(n.ball.x).toBeGreaterThanOrEqual(PADDLE_WIDTH);
    const n2 = step(n, none, DT);
    expect(n2.ball.vx).toBeGreaterThan(0);
    expect(Math.hypot(n2.ball.vx, n2.ball.vy)).toBeCloseTo(Math.hypot(n.ball.vx, n.ball.vy), 5);
  });
  it('right paddle sends the ball left', () => {
    const ay = 200;
    const s = withBall(
      { x: RIGHT_PADDLE_X - BALL_SIZE - 2, y: ay + 40, vx: 400, vy: 0 },
      { ai: { y: ay, targetY: ay + 45, timer: 0 } },
    );
    const n = step(s, none, DT);
    expect(n.ball.vx).toBeLessThan(0);
  });
  it('does not tunnel at max speed and dt=1/30', () => {
    const py = 200;
    let s = withBall(
      { x: 60, y: py + 40, vx: -MAX_BALL_SPEED, vy: 0 },
      { player: { y: py } },
    );
    for (let i = 0; i < 5; i++) s = step(s, none, 1 / 30);
    expect(s.ball.vx).toBeGreaterThan(0);
    expect(s.computerScore).toBe(0);
  });
});

describe('scoring and win (R-07)', () => {
  it('player scores when ball exits right', () => {
    const s = withBall({ x: FIELD_WIDTH - 1, y: 10, vx: 400, vy: 0 });
    const n = step(s, none, DT, { angle: 0.2 });
    expect(n.playerScore).toBe(1);
    expect(n.ball.x + BALL_SIZE / 2).toBe(FIELD_WIDTH / 2);
    expect(Math.hypot(n.ball.vx, n.ball.vy)).toBeCloseTo(BASE_BALL_SPEED, 5);
    expect(n.ball.vy).toBeCloseTo(BASE_BALL_SPEED * Math.sin(0.2), 5);
    expect(n.phase).toBe('playing');
  });
  it('computer scores when ball exits left', () => {
    const s = withBall({ x: -BALL_SIZE + 1, y: 10, vx: -400, vy: 0 }, { player: { y: 300 } });
    const n = step(s, none, DT);
    expect(n.computerScore).toBe(1);
    expect(n.ball.vx).toBeLessThan(0);
  });
  it('injected serve direction overrides', () => {
    const s = withBall({ x: FIELD_WIDTH - 1, y: 10, vx: 400, vy: 0 });
    expect(step(s, none, DT, { angle: 0, dir: -1 }).ball.vx).toBeLessThan(0);
  });
  it('player wins at 10 and state freezes', () => {
    const s = withBall({ x: FIELD_WIDTH - 1, y: 10, vx: 400, vy: 0 }, { playerScore: WIN_SCORE - 1 });
    const n = step(s, none, DT);
    expect(n.phase).toBe('gameover');
    expect(n.winner).toBe('player');
    expect(step(n, { up: true, down: false }, DT)).toBe(n);
  });
  it('computer wins at 10', () => {
    const s = withBall(
      { x: -BALL_SIZE + 1, y: 10, vx: -400, vy: 0 },
      { computerScore: WIN_SCORE - 1, player: { y: 300 } },
    );
    const n = step(s, none, DT);
    expect(n.phase).toBe('gameover');
    expect(n.winner).toBe('computer');
  });
});

describe('phases (R-08)', () => {
  it('step is a no-op outside playing', () => {
    for (const phase of ['ready', 'paused', 'gameover'] as const) {
      const s = { ...createInitialState(), phase };
      expect(step(s, { up: true, down: false }, DT)).toBe(s);
    }
  });
  it('toggle transitions and gameover ignores toggle', () => {
    const r = createInitialState();
    const p = applyCommand(r, 'toggle');
    expect(p.phase).toBe('playing');
    const paused = applyCommand(p, 'toggle');
    expect(paused.phase).toBe('paused');
    expect(paused.ball).toEqual(p.ball);
    expect(applyCommand(paused, 'toggle').phase).toBe('playing');
    const over = { ...p, phase: 'gameover' as const };
    expect(applyCommand(over, 'toggle')).toBe(over);
  });
  it('restart resets to ready 0-0', () => {
    const over = { ...playing({ playerScore: 10, computerScore: 3 }), phase: 'gameover' as const, winner: 'player' as const };
    const n = applyCommand(over, 'restart');
    expect(n.phase).toBe('ready');
    expect(n.playerScore).toBe(0);
    expect(n.computerScore).toBe(0);
    expect(n.winner).toBeNull();
  });
});
