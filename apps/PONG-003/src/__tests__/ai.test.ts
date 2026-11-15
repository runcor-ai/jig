import { describe, expect, it } from 'vitest';
import { aiDirection } from '../game/ai';
import { createInitialState, NO_INPUT, type GameState } from '../game/state';
import { step } from '../game/step';

const rng = () => 0.5;
const playing = (): GameState => {
  const s = createInitialState(rng);
  return { ...s, phase: 'playing', ball: { ...s.ball, vx: 0, vy: 0 } };
};
const centre = (s: GameState) => s.right.y + 40;

describe('R-03 aiDirection', () => {
  it('is 0 within the dead zone, otherwise toward the target', () => {
    expect(aiDirection(250, 250)).toBe(0);
    expect(aiDirection(250, 259)).toBe(0);
    expect(aiDirection(250, 240)).toBe(0);
    expect(aiDirection(250, 261)).toBe(1);
    expect(aiDirection(250, 239)).toBe(-1);
  });
});

describe('R-03 AI paddle', () => {
  it('never moves more than 260*dt per step', () => {
    let s = playing();
    s = { ...s, ball: { ...s.ball, y: 20 } };
    for (let i = 0; i < 60; i++) {
      const before = s.right.y;
      s = step(s, NO_INPUT, 0.016, rng);
      expect(Math.abs(s.right.y - before)).toBeLessThanOrEqual(260 * 0.016 + 1e-9);
    }
  });
  it('lags a ball moving vertically faster than 260 px/s', () => {
    let s = playing();
    s = { ...s, right: { ...s.right, y: 360 }, ball: { ...s.ball, x: 300, y: 394, vy: -500 } };
    for (let i = 0; i < 30; i++) s = step(s, NO_INPUT, 1 / 60, rng);
    expect(centre(s)).toBeGreaterThan(s.ball.y + 6 + 20);
  });
  it('responds to a jump in ball y only after about 150 ms', () => {
    let s = playing();
    for (let i = 0; i < 20; i++) s = step(s, NO_INPUT, 0.01, rng);
    s = { ...s, ball: { ...s.ball, y: 44 } };
    for (let i = 0; i < 10; i++) s = step(s, NO_INPUT, 0.01, rng); // 100 ms
    expect(s.right.y).toBe(210);
    for (let i = 0; i < 20; i++) s = step(s, NO_INPUT, 0.01, rng); // 300 ms
    expect(s.right.y).toBeLessThan(210);
  });
  it('is clamped to the playfield', () => {
    let s = playing();
    s = { ...s, ball: { ...s.ball, y: 0 } };
    for (let i = 0; i < 100; i++) s = step(s, NO_INPUT, 0.05, rng);
    expect(s.right.y).toBe(0);
  });
});
