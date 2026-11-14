import { describe, expect, it } from 'vitest';
import { updateAI } from './ai';
import {
  AI_DEAD_ZONE,
  AI_MAX_SPEED,
  AI_REACTION_SECONDS,
  FIELD_HEIGHT,
  PADDLE_HEIGHT,
  PLAYER_SPEED,
} from './constants';
import { createInitialState } from './state';
import { step } from './step';
import type { GameState } from './types';

describe('AI (R-04)', () => {
  it('is slower than the player', () => {
    expect(AI_MAX_SPEED).toBeLessThan(PLAYER_SPEED);
  });

  it('never exceeds max speed per step', () => {
    const ai = { y: 100, targetY: 450, timer: 0 };
    const n = updateAI(ai, 450, 1 / 60);
    expect(Math.abs(n.y - ai.y)).toBeLessThanOrEqual(AI_MAX_SPEED / 60 + 1e-9);
    const big = updateAI(ai, 450, 1 / 30);
    expect(Math.abs(big.y - ai.y)).toBeLessThanOrEqual(AI_MAX_SPEED / 30 + 1e-9);
  });

  it('keeps the old target until the reaction interval elapses', () => {
    let ai = { y: 200, targetY: 250, timer: 0 };
    ai = updateAI(ai, 50, 0.05); // ball moved to y=50 immediately
    expect(ai.targetY).toBe(250);
    ai = updateAI(ai, 50, 0.05);
    expect(ai.targetY).toBe(250);
    ai = updateAI(ai, 50, AI_REACTION_SECONDS);
    expect(ai.targetY).toBe(50);
  });

  it('does not move inside the dead zone', () => {
    const y = 200;
    const ai = { y, targetY: y + PADDLE_HEIGHT / 2 + AI_DEAD_ZONE - 1, timer: 0 };
    expect(updateAI(ai, ai.targetY, 1 / 60).y).toBe(y);
  });

  it('stays within the playfield', () => {
    let ai = { y: 5, targetY: -500, timer: 0 };
    for (let i = 0; i < 30; i++) ai = updateAI(ai, -500, 1 / 30);
    expect(ai.y).toBe(0);
    ai = { y: FIELD_HEIGHT - PADDLE_HEIGHT - 5, targetY: 5000, timer: 0 };
    for (let i = 0; i < 30; i++) ai = updateAI(ai, 5000, 1 / 30);
    expect(ai.y).toBe(FIELD_HEIGHT - PADDLE_HEIGHT);
  });

  it('can be beaten by a fast steep ball', () => {
    let s: GameState = { ...createInitialState(), phase: 'playing' };
    s = { ...s, ball: { x: 400, y: 20, vx: 700, vy: 900 } };
    for (let i = 0; i < 120 && s.playerScore === 0; i++) {
      s = step(s, { up: false, down: false }, 1 / 60);
    }
    expect(s.playerScore).toBe(1);
  });
});
