import { describe, expect, it } from 'vitest';
import {
  AI_DEAD_ZONE,
  AI_SPEED,
  BALL_MAX_SPEED,
  BALL_SIZE,
  HEIGHT,
  LEFT_PADDLE_X,
  MAX_VY,
  PADDLE_H,
  PADDLE_W,
  RIGHT_PADDLE_X,
  WIDTH,
  WIN_SCORE,
} from '../game/config';
import { computeAiMove } from '../game/ai';
import { createInitialState, resetBall, step, type GameState } from '../game/logic';

const base = (over: Partial<GameState> = {}): GameState => ({ ...createInitialState(), ...over });
const rng = () => 0.5; // vy = 0 on serve
const DT = 1 / 60;

describe('paddle movement (R-02)', () => {
  it('moves up and down by input and stops with no input', () => {
    const s = base({ leftY: 200, ball: { x: 400, y: 250, vx: 0, vy: 0 } });
    expect(step(s, { dir: -1 }, DT, rng).leftY).toBeLessThan(200);
    expect(step(s, { dir: 1 }, DT, rng).leftY).toBeGreaterThan(200);
    expect(step(s, { dir: 0 }, DT, rng).leftY).toBe(200);
  });
  it('clamps at the field edges', () => {
    const top = base({ leftY: 1, ball: { x: 400, y: 250, vx: 0, vy: 0 } });
    expect(step(top, { dir: -1 }, 1, rng).leftY).toBe(0);
    const bottom = base({ leftY: HEIGHT - PADDLE_H - 1, ball: { x: 400, y: 250, vx: 0, vy: 0 } });
    expect(step(bottom, { dir: 1 }, 1, rng).leftY).toBe(HEIGHT - PADDLE_H);
  });
});

describe('ball movement and bouncing (R-03)', () => {
  it('moves by velocity', () => {
    const s = base({ ball: { x: 400, y: 250, vx: 100, vy: 60 } });
    const n = step(s, { dir: 0 }, 0.1, rng);
    expect(n.ball.x).toBeCloseTo(410);
    expect(n.ball.y).toBeCloseTo(256);
  });
  it('reflects off the top wall', () => {
    const s = base({ ball: { x: 400, y: 2, vx: 0, vy: -100 } });
    const n = step(s, { dir: 0 }, 0.1, rng);
    expect(n.ball.vy).toBeGreaterThan(0);
    expect(n.ball.y).toBeGreaterThanOrEqual(0);
  });
  it('reflects off the bottom wall', () => {
    const s = base({ ball: { x: 400, y: HEIGHT - BALL_SIZE - 2, vx: 0, vy: 100 } });
    const n = step(s, { dir: 0 }, 0.1, rng);
    expect(n.ball.vy).toBeLessThan(0);
    expect(n.ball.y).toBeLessThanOrEqual(HEIGHT - BALL_SIZE);
  });
  it('flips vx on the left paddle and moves ball outside it', () => {
    const s = base({ leftY: 200, ball: { x: LEFT_PADDLE_X + PADDLE_W + 1, y: 230, vx: -300, vy: 0 } });
    const n = step(s, { dir: 0 }, DT, rng);
    expect(n.ball.vx).toBeGreaterThan(0);
    expect(n.ball.x).toBeGreaterThanOrEqual(LEFT_PADDLE_X + PADDLE_W);
  });
  it('flips vx on the right paddle and moves ball outside it', () => {
    const s = base({ rightY: 200, ball: { x: RIGHT_PADDLE_X - BALL_SIZE - 1, y: 234, vx: 300, vy: 0 } });
    const n = step(s, { dir: 0 }, DT, rng);
    expect(n.ball.vx).toBeLessThan(0);
    expect(n.ball.x + BALL_SIZE).toBeLessThanOrEqual(RIGHT_PADDLE_X);
  });
  it('sets vy from hit offset: top negative, bottom positive', () => {
    const topHit = step(
      base({ leftY: 200, ball: { x: LEFT_PADDLE_X + PADDLE_W, y: 190, vx: -300, vy: 0 } }),
      { dir: 0 }, DT, rng);
    const bottomHit = step(
      base({ leftY: 200, ball: { x: LEFT_PADDLE_X + PADDLE_W, y: 270, vx: -300, vy: 0 } }),
      { dir: 0 }, DT, rng);
    expect(topHit.ball.vy).toBeLessThan(0);
    expect(bottomHit.ball.vy).toBeGreaterThan(0);
  });
  it('caps ball speed', () => {
    const s = base({ leftY: 200, ball: { x: LEFT_PADDLE_X + PADDLE_W, y: 275, vx: -BALL_MAX_SPEED, vy: 0 } });
    const n = step(s, { dir: 0 }, DT, rng);
    expect(Math.hypot(n.ball.vx, n.ball.vy)).toBeLessThanOrEqual(BALL_MAX_SPEED + 1e-6);
  });
});

describe('AI (R-04)', () => {
  const st = (ballY: number, rightY: number) => base({ rightY, ball: { x: 400, y: ballY, vx: 0, vy: 0 } });
  it('moves up toward a ball above, limited by aiSpeed', () => {
    const y = computeAiMove(st(0, 200), DT);
    expect(y).toBeLessThan(200);
    expect(200 - y).toBeLessThanOrEqual(AI_SPEED * DT + 1e-9);
  });
  it('moves down toward a ball below, limited by aiSpeed', () => {
    const y = computeAiMove(st(480, 200), DT);
    expect(y).toBeGreaterThan(200);
    expect(y - 200).toBeLessThanOrEqual(AI_SPEED * DT + 1e-9);
  });
  it('does not overshoot a nearby ball', () => {
    const rightY = 200;
    const target = rightY + PADDLE_H / 2 + AI_DEAD_ZONE + 2; // ball centre
    const y = computeAiMove(st(target - BALL_SIZE / 2, rightY), 10);
    expect(y + PADDLE_H / 2).toBeCloseTo(target);
  });
  it('is slower than max ball vertical speed', () => {
    expect(AI_SPEED).toBeLessThan(MAX_VY);
  });
  it('stays in the field', () => {
    expect(computeAiMove(st(-100, 0), 1)).toBe(0);
    expect(computeAiMove(st(1000, HEIGHT - PADDLE_H), 1)).toBe(HEIGHT - PADDLE_H);
  });
  it('does not move inside the dead zone', () => {
    const rightY = 200;
    const centre = rightY + PADDLE_H / 2;
    expect(computeAiMove(st(centre + AI_DEAD_ZONE - 1 - BALL_SIZE / 2, rightY), DT)).toBe(rightY);
  });
});

describe('scoring (R-05)', () => {
  it('computer scores when ball passes left edge; serves toward player', () => {
    const s = base({ leftY: 0, ball: { x: -BALL_SIZE - 1, y: 400, vx: -100, vy: 0 } });
    const n = step(s, { dir: 0 }, 0.001, rng);
    expect(n.computerScore).toBe(1);
    expect(n.playerScore).toBe(0);
    expect(n.ball.x).toBe((WIDTH - BALL_SIZE) / 2);
    expect(n.ball.y).toBe((HEIGHT - BALL_SIZE) / 2);
    expect(n.ball.vx).toBeLessThan(0);
  });
  it('player scores when ball passes right edge; serves toward computer', () => {
    const s = base({ rightY: 0, ball: { x: WIDTH + 1, y: 400, vx: 100, vy: 0 } });
    const n = step(s, { dir: 0 }, 0.001, rng);
    expect(n.playerScore).toBe(1);
    expect(n.computerScore).toBe(0);
    expect(n.ball.x).toBe((WIDTH - BALL_SIZE) / 2);
    expect(n.ball.vx).toBeGreaterThan(0);
  });
  it('resetBall centres and directs the serve', () => {
    expect(resetBall(1).vx).toBeGreaterThan(0);
    expect(resetBall(-1).vx).toBeLessThan(0);
  });
});

describe('win condition (R-06)', () => {
  it('player reaching 10 ends the game', () => {
    const s = base({ playerScore: WIN_SCORE - 1, rightY: 0, ball: { x: WIDTH + 1, y: 400, vx: 100, vy: 0 } });
    const n = step(s, { dir: 0 }, 0.001, rng);
    expect(n.playerScore).toBe(WIN_SCORE);
    expect(n.status).toBe('gameover');
    expect(n.winner).toBe('player');
  });
  it('computer reaching 10 ends the game', () => {
    const s = base({ computerScore: WIN_SCORE - 1, leftY: 0, ball: { x: -BALL_SIZE - 1, y: 400, vx: -100, vy: 0 } });
    const n = step(s, { dir: 0 }, 0.001, rng);
    expect(n.status).toBe('gameover');
    expect(n.winner).toBe('computer');
  });
  it('stops updating after gameover so scores never exceed 10', () => {
    const s = base({ playerScore: WIN_SCORE, status: 'gameover', winner: 'player', ball: { x: WIDTH + 1, y: 400, vx: 100, vy: 0 } });
    const n = step(s, { dir: 1 }, 1, rng);
    expect(n).toBe(s);
  });
  it('does not update while paused (R-10)', () => {
    const s = base({ status: 'paused' });
    expect(step(s, { dir: 1 }, 1, rng)).toBe(s);
  });
});
