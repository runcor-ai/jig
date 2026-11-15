import { describe, expect, it } from 'vitest';
import { clearLines, collides, createBoard, dropDistance, merge } from './board';
import type { Board } from './board';
import { spawnPiece } from './pieces';

const fullRow = () => Array(10).fill('T') as Board[number];

describe('board (R-01, R-03, R-06)', () => {
  it('createBoard is 20x10 empty', () => {
    const b = createBoard();
    expect(b).toHaveLength(20);
    for (const r of b) {
      expect(r).toHaveLength(10);
      expect(r.every((c) => c === null)).toBe(true);
    }
  });

  it('collides on walls, floor and locked cells', () => {
    const b = createBoard();
    const p = { ...spawnPiece('O'), y: 5 };
    expect(collides(b, p)).toBe(false);
    expect(collides(b, { ...p, x: -1 })).toBe(true);
    expect(collides(b, { ...p, x: 9 })).toBe(true);
    expect(collides(b, { ...p, y: 19 })).toBe(true);
    b[6][5] = 'T';
    expect(collides(b, p)).toBe(true);
  });

  it('merge writes piece cells without mutating input', () => {
    const b = createBoard();
    const p = { ...spawnPiece('O'), y: 18 };
    const m = merge(b, p);
    expect(m[18][4]).toBe('O');
    expect(m[19][5]).toBe('O');
    expect(b[18][4]).toBeNull();
  });

  it('clears 1 to 4 rows and pads empty rows on top', () => {
    for (let n = 1; n <= 4; n++) {
      const b = createBoard();
      for (let i = 0; i < n; i++) b[19 - i] = fullRow();
      const { board, cleared } = clearLines(b);
      expect(cleared).toBe(n);
      expect(board).toHaveLength(20);
      expect(board.every((r) => r.every((c) => c === null))).toBe(true);
    }
  });

  it('keeps non-full rows in order, handles non-adjacent full rows', () => {
    const b = createBoard();
    b[19] = fullRow();
    b[18][0] = 'I';
    b[17] = fullRow();
    b[16][1] = 'J';
    const { board, cleared } = clearLines(b);
    expect(cleared).toBe(2);
    expect(board[19][0]).toBe('I');
    expect(board[18][1]).toBe('J');
    expect(board[17].every((c) => c === null)).toBe(true);
  });

  it('dropDistance reaches the floor', () => {
    const p = spawnPiece('O'); // y 0, occupies rows 0-1
    expect(dropDistance(createBoard(), p)).toBe(18);
  });
});
