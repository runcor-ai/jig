import { describe, expect, it } from 'vitest';
import * as C from '../game/config';
import type { GameState } from '../game/config';
import { createInitialState, pause, restart, startOrTogglePause, step } from '../game/logic';
import { moveAi } from '../game/ai';
import { keyToAction } from '../hooks/useKeyboard';

const none = { up: false, down: false };
const playing = (): GameState => ({ ...createInitialState(), status: 'playing' });

describe('state machine', () => {
  it('starts ready, space starts, space pauses/resumes', () => {
    let s = createInitialState();
    expect(s.status).toBe('ready');
    expect(step(s, none, 0.016)).toBe(s);
    s = startOrTogglePause(s); expect(s.status).toBe('playing');
    s = startOrTogglePause(s); expect(s.status).toBe('paused');
    s = startOrTogglePause(s); expect(s.status).toBe('playing');
    expect(pause(s).status).toBe('paused');
  });
  it('first serve goes toward the player', () => {
    expect(createInitialState().ball.vx).toBeLessThan(0);
  });
});

describe('paddle', () => {
  it('moves and clamps', () => {
    let s = playing();
    const y0 = s.playerY;
    s = step(s, { up: true, down: false }, 0.016);
    expect(s.playerY).toBeLessThan(y0);
    for (let i = 0; i < 200; i++) s = { ...step(s, { up: true, down: false }, 0.016), ball: playing().ball };
    expect(s.playerY).toBe(0);
    for (let i = 0; i < 200; i++) s = { ...step(s, { up: false, down: true }, 0.016), ball: playing().ball };
    expect(s.playerY).toBe(C.MAX_PADDLE_Y);
  });
});

describe('ball', () => {
  it('bounces off top and bottom walls', () => {
    let s = { ...playing(), ball: { x: 400, y: 1, vx: 0, vy: -300 } };
    expect(step(s, none, 0.016).ball.vy).toBeGreaterThan(0);
    s = { ...playing(), ball: { x: 400, y: C.MAX_BALL_Y - 1, vx: 0, vy: 300 } };
    expect(step(s, none, 0.016).ball.vy).toBeLessThan(0);
  });
  it('reverses at paddle with angle depending on hit position', () => {
    const mk = (offset: number) => ({
      ...playing(), playerY: 200,
      ball: { x: C.PLAYER_X + C.PADDLE_W + 1, y: 200 + C.PADDLE_H / 2 - C.BALL_SIZE / 2 + offset, vx: -360, vy: 0 },
    });
    const mid = step(mk(0), none, 0.016).ball;
    const low = step(mk(35), none, 0.016).ball;
    const high = step(mk(-35), none, 0.016).ball;
    expect(mid.vx).toBeGreaterThan(0);
    expect(Math.abs(mid.vy)).toBeLessThan(1);
    expect(low.vy).toBeGreaterThan(0);
    expect(high.vy).toBeLessThan(0);
  });
  it('bounces off the computer paddle', () => {
    const s = { ...playing(), aiY: 200, ball: { x: C.AI_X - C.BALL_SIZE - 1, y: 230, vx: 360, vy: 0 } };
    expect(step(s, none, 0.016).ball.vx).toBeLessThan(0);
  });
  it('speed never exceeds max', () => {
    const s = { ...playing(), playerY: 200, ball: { x: C.PLAYER_X + C.PADDLE_W + 1, y: 230, vx: -C.MAX_BALL_SPEED, vy: 0 } };
    const b = step(s, none, 0.016).ball;
    expect(Math.hypot(b.vx, b.vy)).toBeLessThanOrEqual(C.MAX_BALL_SPEED + 1e-9);
  });
});

describe('scoring', () => {
  it('left exit scores for computer, resets to centre, alternates serve', () => {
    const s = { ...playing(), playerY: 0, ball: { x: -C.BALL_SIZE - 1, y: 400, vx: -100, vy: 0 } };
    const n = step(s, none, 0.016);
    expect(n.aiScore).toBe(1);
    expect(n.playerScore).toBe(0);
    expect(n.ball.x).toBe((C.FIELD_W - C.BALL_SIZE) / 2);
    expect(n.serveDirection).toBe(1);
    expect(n.ball.vx).toBeGreaterThan(0);
  });
  it('right exit scores for player', () => {
    const s = { ...playing(), aiY: 0, ball: { x: C.FIELD_W + 1, y: 400, vx: 100, vy: 0 } };
    expect(step(s, none, 0.016).playerScore).toBe(1);
  });
  it('wins at 10 and freezes', () => {
    const s = { ...playing(), playerScore: 9, aiY: 0, ball: { x: C.FIELD_W + 1, y: 400, vx: 100, vy: 0 } };
    const n = step(s, none, 0.016);
    expect(n.playerScore).toBe(10);
    expect(n.status).toBe('over');
    expect(n.winner).toBe('player');
    expect(step(n, { up: true, down: false }, 0.016)).toBe(n);
    expect(startOrTogglePause(n)).toBe(n);
  });
  it('computer can win', () => {
    const s = { ...playing(), aiScore: 9, playerY: 0, ball: { x: -C.BALL_SIZE - 1, y: 400, vx: -100, vy: 0 } };
    expect(step(s, none, 0.016).winner).toBe('computer');
  });
});

describe('restart', () => {
  it('resets everything and plays', () => {
    const r = restart();
    expect(r.playerScore + r.aiScore).toBe(0);
    expect(r.status).toBe('playing');
    expect(r.winner).toBeNull();
    expect(r.serveDirection).toBe(-1);
  });
});

describe('ai', () => {
  it('moves toward ball, capped speed, in bounds', () => {
    const dt = 0.016;
    expect(moveAi(100, 400, dt)).toBeGreaterThan(100);
    expect(moveAi(300, 0, dt)).toBeLessThan(300);
    expect(moveAi(100, 400, dt) - 100).toBeLessThanOrEqual(C.AI_SPEED * dt + 1e-9);
    expect(moveAi(0, -500, dt)).toBe(0);
    expect(moveAi(C.MAX_PADDLE_Y, 9999, dt)).toBe(C.MAX_PADDLE_Y);
  });
  it('cap is below max ball vertical speed', () => {
    expect(C.AI_SPEED).toBeLessThan(C.MAX_BALL_SPEED * Math.sin(C.MAX_BOUNCE_ANGLE));
  });
});

describe('validation', () => {
  it('whitelists keys', () => {
    expect(keyToAction('ArrowUp')).toBe('up');
    expect(keyToAction('w')).toBe('up');
    expect(keyToAction('S')).toBe('down');
    expect(keyToAction(' ')).toBe('toggle');
    expect(keyToAction('x')).toBeNull();
    expect(keyToAction('Enter')).toBeNull();
  });
  it('clamp handles NaN and range', () => {
    expect(C.clamp(NaN, 0, 5)).toBe(0);
    expect(C.clamp(9, 0, 5)).toBe(5);
    expect(() => C.validateConfig()).not.toThrow();
  });
  it('long simulation keeps values in range', () => {
    let s = restart();
    for (let i = 0; i < 20000 && s.status === 'playing'; i++) {
      s = step(s, { up: i % 100 < 50, down: i % 100 >= 50 }, 1 / 60);
      expect(s.playerY).toBeGreaterThanOrEqual(0);
      expect(s.playerY).toBeLessThanOrEqual(C.MAX_PADDLE_Y);
      expect(s.ball.y).toBeGreaterThanOrEqual(0);
      expect(s.ball.y).toBeLessThanOrEqual(C.MAX_BALL_Y);
      expect(Math.hypot(s.ball.vx, s.ball.vy)).toBeLessThanOrEqual(C.MAX_BALL_SPEED + 1e-6);
      expect(s.playerScore).toBeLessThanOrEqual(10);
      expect(s.aiScore).toBeLessThanOrEqual(10);
    }
  });
});
