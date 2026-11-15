import { describe, expect, it } from 'vitest';
import { createInitialState, serveBall, NO_INPUT, type Ball, type GameState } from '../game/state';
import { step } from '../game/step';

const rng = () => 0.5;
const deg = (r: number) => (r * 180) / Math.PI;

function playing(over: Partial<GameState> = {}): GameState {
  return { ...createInitialState(rng), phase: 'playing', ...over };
}
function withBall(b: Partial<Ball>, over: Partial<GameState> = {}): GameState {
  const s = playing(over);
  return { ...s, ball: { ...s.ball, ...b } };
}

describe('R-01 initial state', () => {
  it('has the specified dimensions and positions', () => {
    const s = createInitialState();
    expect(s.left).toEqual({ x: 20, y: 210, width: 12, height: 80 });
    expect(s.right).toEqual({ x: 768, y: 210, width: 12, height: 80 });
    expect(s.ball.width).toBe(12);
    expect(s.ball.height).toBe(12);
    expect(s.ball.x + 6).toBe(400);
    expect(s.ball.y + 6).toBe(250);
    expect(s.phase).toBe('ready');
  });
});

describe('R-02 player movement', () => {
  const still = { vx: 0, vy: 0 };
  it('moves up and down at 400 px/s', () => {
    const up = step(withBall(still), { up: true, down: false }, 0.01, rng);
    expect(up.left.y).toBeCloseTo(206);
    const down = step(withBall(still), { up: false, down: true }, 0.01, rng);
    expect(down.left.y).toBeCloseTo(214);
  });
  it('is clamped to the playfield', () => {
    let s = withBall(still);
    for (let i = 0; i < 40; i++) s = step(s, { up: true, down: false }, 0.05, rng);
    expect(s.left.y).toBe(0);
    for (let i = 0; i < 40; i++) s = step(s, { up: false, down: true }, 0.05, rng);
    expect(s.left.y).toBe(420);
  });
  it('does not move when both are held', () => {
    const s = step(withBall(still), { up: true, down: true }, 0.05, rng);
    expect(s.left.y).toBe(210);
  });
});

describe('R-04 wall bounces', () => {
  it('reflects off the top', () => {
    const s = step(withBall({ x: 300, y: 2, vx: 100, vy: -300 }), NO_INPUT, 0.016, rng);
    expect(s.ball.vy).toBeGreaterThan(0);
    expect(s.ball.y).toBeGreaterThanOrEqual(0);
    expect(s.ball.vx).toBe(100);
  });
  it('reflects off the bottom', () => {
    const s = step(withBall({ x: 300, y: 486, vx: 100, vy: 300 }), NO_INPUT, 0.016, rng);
    expect(s.ball.vy).toBeLessThan(0);
    expect(s.ball.y + s.ball.height).toBeLessThanOrEqual(500);
    expect(s.ball.vx).toBe(100);
  });
});

describe('R-05 paddle bounces', () => {
  const hit = (y: number, extra: Partial<Ball> = {}) =>
    step(withBall({ x: 34, y, vx: -300, vy: 0, ...extra }), NO_INPUT, 0.01, rng).ball;

  it('centre hit reverses vx with vy about 0', () => {
    const b = hit(244);
    expect(b.vx).toBeGreaterThan(0);
    expect(b.vy).toBeCloseTo(0);
    expect(b.x).toBeGreaterThanOrEqual(32);
  });
  it('top edge gives about -60 degrees, bottom edge about +60', () => {
    const t = hit(204);
    expect(deg(Math.atan2(t.vy, t.vx))).toBeCloseTo(-60);
    const b = hit(284);
    expect(deg(Math.atan2(b.vy, b.vx))).toBeCloseTo(60);
  });
  it('multiplies speed by 1.05', () => {
    const b = hit(244, { vy: 100 });
    expect(Math.hypot(b.vx, b.vy)).toBeCloseTo(Math.hypot(-300, 100) * 1.05);
  });
  it('caps speed at 900', () => {
    const b = step(withBall({ x: 36, y: 244, vx: -880, vy: 0 }), NO_INPUT, 0.01, rng).ball;
    expect(Math.hypot(b.vx, b.vy)).toBeCloseTo(900);
  });
  it('right paddle reflects leftwards', () => {
    const b = step(withBall({ x: 760, y: 244, vx: 300, vy: 0 }), NO_INPUT, 0.01, rng).ball;
    expect(b.vx).toBeLessThan(0);
    expect(b.x + b.width).toBeLessThanOrEqual(768);
  });
  it('does not bounce a ball moving away', () => {
    const b = step(withBall({ x: 25, y: 244, vx: 300, vy: 0 }), NO_INPUT, 0.01, rng).ball;
    expect(b.vx).toBe(300);
  });
  it('does not bounce twice on consecutive steps', () => {
    let s = step(withBall({ x: 34, y: 244, vx: -300, vy: 0 }), NO_INPUT, 0.01, rng);
    const speed = Math.hypot(s.ball.vx, s.ball.vy);
    s = step(s, NO_INPUT, 0.01, rng);
    expect(Math.hypot(s.ball.vx, s.ball.vy)).toBeCloseTo(speed);
    expect(s.ball.vx).toBeGreaterThan(0);
  });
});

describe('R-06 serve', () => {
  it('has speed 300 and angle within +-30 degrees', () => {
    for (const r of [0, 0.25, 0.5, 1]) {
      const b = serveBall(() => r, 1);
      expect(Math.hypot(b.vx, b.vy)).toBeCloseTo(300);
      expect(Math.abs(deg(Math.atan2(b.vy, b.vx)))).toBeLessThanOrEqual(30.0001);
    }
    expect(deg(Math.atan2(serveBall(() => 0, 1).vy, serveBall(() => 0, 1).vx))).toBeCloseTo(-30);
  });
  it('first serve goes toward the player', () => {
    expect(createInitialState(rng).ball.vx).toBeLessThan(0);
  });
  it('after a point the ball is centred, at speed 300, toward the conceding side', () => {
    const p = step(withBall({ x: 799, vx: 900, vy: 0 }), NO_INPUT, 0.05, rng);
    expect(p.ball.x + 6).toBe(400);
    expect(p.ball.y + 6).toBe(250);
    expect(Math.hypot(p.ball.vx, p.ball.vy)).toBeCloseTo(300);
    expect(p.ball.vx).toBeGreaterThan(0); // computer conceded
    const c = step(withBall({ x: -10, vx: -300, vy: 0 }), NO_INPUT, 0.05, rng);
    expect(c.ball.vx).toBeLessThan(0); // player conceded
  });
});

describe('R-07 scoring', () => {
  it('left exit scores for the computer only', () => {
    const s = step(withBall({ x: -13, vx: -300, vy: 0 }), NO_INPUT, 0.01, rng);
    expect(s.scores).toEqual({ player: 0, computer: 1 });
    expect(s.phase).toBe('serving');
  });
  it('right exit scores for the player only', () => {
    const s = step(withBall({ x: 800, vx: 300, vy: 0 }), NO_INPUT, 0.01, rng);
    expect(s.scores).toEqual({ player: 1, computer: 0 });
  });
  it('awards one point per exit and holds the ball for 1 s', () => {
    let s = step(withBall({ x: -13, vx: -300, vy: 0 }), NO_INPUT, 0.01, rng);
    const ball = s.ball;
    for (let i = 0; i < 18; i++) s = step(s, NO_INPUT, 0.05, rng); // 0.9 s
    expect(s.phase).toBe('serving');
    expect(s.ball).toEqual(ball);
    for (let i = 0; i < 4; i++) s = step(s, NO_INPUT, 0.05, rng); // 1.1 s
    expect(s.phase).toBe('playing');
    s = step(s, NO_INPUT, 0.05, rng);
    expect(s.ball.x).not.toBe(ball.x);
    expect(s.scores).toEqual({ player: 0, computer: 1 });
  });
});

describe('R-08 win condition', () => {
  it('player reaches 10 and the game is over', () => {
    const s = step(withBall({ x: 801, vx: 300, vy: 0 }, { scores: { player: 9, computer: 4 } }), NO_INPUT, 0.01, rng);
    expect(s.scores).toEqual({ player: 10, computer: 4 });
    expect(s.phase).toBe('over');
    expect(s.winner).toBe('player');
  });
  it('computer reaches 10', () => {
    const s = step(withBall({ x: -20, vx: -300, vy: 0 }, { scores: { player: 2, computer: 9 } }), NO_INPUT, 0.01, rng);
    expect(s.winner).toBe('computer');
    expect(s.scores.computer).toBe(10);
  });
  it('over phase is inert', () => {
    const over = step(withBall({ x: 801, vx: 300, vy: 0 }, { scores: { player: 9, computer: 0 } }), NO_INPUT, 0.01, rng);
    expect(step(over, { up: true, down: false }, 0.05, rng)).toBe(over);
    expect(over.scores.player).toBe(10);
  });
});

describe('R-09 inert phases', () => {
  it('ready and paused do not move anything', () => {
    for (const phase of ['ready', 'paused'] as const) {
      const s = { ...createInitialState(rng), phase };
      expect(step(s, { up: true, down: false }, 0.05, rng)).toBe(s);
    }
  });
});

describe('R-12 no tunnelling', () => {
  it('a 900 px/s ball with dt 0.05 still bounces off the paddle', () => {
    const s = step(withBall({ x: 40, y: 244, vx: -900, vy: 0 }), NO_INPUT, 0.05, rng);
    expect(s.ball.vx).toBeGreaterThan(0);
    expect(s.scores.computer).toBe(0);
  });
  it('same for the right paddle', () => {
    const s = step(withBall({ x: 740, y: 244, vx: 900, vy: 0 }), NO_INPUT, 0.05, rng);
    expect(s.ball.vx).toBeLessThan(0);
  });
});
