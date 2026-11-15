import { describe, expect, it } from 'vitest';
import { createBoard } from './board';
import type { Board } from './board';
import { newGame, reduce } from './game';
import type { GameState } from './game';
import { pieceCells, spawnPiece } from './pieces';

const rng = () => 0.3; // always 'T'
const base = (o: Partial<GameState> = {}): GameState => ({ ...newGame(rng), ...o });

describe('reducer', () => {
  it('newGame starts playing, empty', () => {
    const s = newGame(rng);
    expect(s.status).toBe('playing');
    expect([s.score, s.level, s.rows]).toEqual([0, 1, 0]);
  });

  it('moves left/right and rejects walls and locked cells (R-03)', () => {
    const s = base();
    expect(reduce(s, 'left', rng).active.x).toBe(s.active.x - 1);
    expect(reduce(s, 'right', rng).active.x).toBe(s.active.x + 1);
    const wall = base({ active: { ...s.active, x: 0 } });
    expect(reduce(wall, 'left', rng)).toBe(wall);
    const b = createBoard();
    b[0][s.active.x + 3] = 'I';
    b[1][s.active.x + 3] = 'I';
    const blocked = base({ board: b });
    expect(reduce(blocked, 'right', rng)).toBe(blocked);
  });

  it('rotates clockwise; kicks off a wall; rejects when blocked (R-04)', () => {
    const s = base({ active: { kind: 'I', rotation: 1, x: -2, y: 5 } }); // vertical I at column 0
    const r = reduce(s, 'rotate', rng);
    expect(r.active.rotation).toBe(2);
    expect(pieceCells(r.active).every(([x]) => x >= 0 && x < 10)).toBe(true);
    expect(reduce(base(), 'rotate', rng).active.rotation).toBe(1);

    // Boxed in: T vertical with solid neighbours so no kick fits
    const b: Board = createBoard();
    for (let y = 0; y < 20; y++) for (let x = 0; x < 10; x++) b[y][x] = 'J';
    const t = { kind: 'T' as const, rotation: 0, x: 3, y: 5 };
    for (const [x, y] of pieceCells(t)) b[y][x] = null;
    const boxed = base({ board: b, active: t });
    expect(reduce(boxed, 'rotate', rng)).toBe(boxed);
  });

  it('tick and soft drop move down; tick locks when blocked (R-05)', () => {
    const s = base();
    expect(reduce(s, 'tick', rng).active.y).toBe(1);
    expect(reduce(s, 'softDrop', rng).active.y).toBe(1);
    const low = base({ active: { ...s.active, y: 18 } }); // T occupies rows 18-19
    const t = reduce(low, 'tick', rng);
    expect(t.board[19][s.active.x + 1]).toBe('T');
    expect(t.active.y).toBe(0);
  });

  it('hard drop locks at once at the lowest row (R-05, R-06)', () => {
    const s = base();
    const h = reduce(s, 'hardDrop', rng);
    expect(h.board[19].some((c) => c === 'T')).toBe(true);
    expect(h.active.y).toBe(0);
  });

  it('line clear updates score, rows, level (R-06, R-07, R-08)', () => {
    const b = createBoard();
    b[19] = Array(10).fill('J').map((c, i) => (i < 4 ? null : c)) as Board[number];
    const s = base({ board: b, active: { kind: 'I', rotation: 0, x: 0, y: 0 } });
    const r = reduce(s, 'hardDrop', rng);
    expect(r.score).toBe(100);
    expect(r.rows).toBe(1);
    expect(r.board[19].every((c) => c === null)).toBe(true);
    const lv = reduce(base({ board: b, rows: 9, active: s.active }), 'hardDrop', rng);
    expect(lv.rows).toBe(10);
    expect(lv.level).toBe(2);
  });

  it('game over when spawn collides; ignores input except restart (R-10)', () => {
    const b = createBoard();
    for (const x of [3, 4, 5, 6]) {
      b[0][x] = 'J';
      b[1][x] = 'J';
    }
    const s = base({ board: b, active: { kind: 'I', rotation: 0, x: 0, y: 10 } });
    const over = reduce(s, 'hardDrop', rng);
    expect(over.status).toBe('over');
    for (const a of ['left', 'right', 'rotate', 'softDrop', 'hardDrop', 'tick', 'togglePause'] as const) {
      expect(reduce({ ...over }, a, rng)).toEqual(over);
    }
    const fresh = reduce({ ...over, score: 500 }, 'restart', rng);
    expect(fresh.status).toBe('playing');
    expect([fresh.score, fresh.level, fresh.rows]).toEqual([0, 1, 0]);
    expect(fresh.board.flat().every((c) => c === null)).toBe(true);
  });

  it('pause toggles and blocks input (R-11)', () => {
    const s = base();
    const p = reduce(s, 'togglePause', rng);
    expect(p.status).toBe('paused');
    for (const a of ['left', 'right', 'rotate', 'softDrop', 'hardDrop', 'tick'] as const) {
      expect(reduce(p, a, rng)).toBe(p);
    }
    expect(reduce(p, 'togglePause', rng).status).toBe('playing');
  });

  it('spawn uses the next piece', () => {
    const s = base({ next: 'O' });
    const r = reduce(s, 'hardDrop', rng);
    expect(r.active).toEqual(spawnPiece('O'));
  });
});
