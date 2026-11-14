import { describe, expect, it } from 'vitest';
import { BOARD_HEIGHT, BOARD_WIDTH, clearFullRows, collides, createBoard, mergePiece, type Board } from './board';
import { PIECES, PIECE_KINDS } from './pieces';

function fullRow(board: Board, y: number) {
  board[y] = Array(BOARD_WIDTH).fill('tee');
}

describe('R-01 board and pieces', () => {
  it('createBoard returns 20 rows of 10 empty cells', () => {
    const b = createBoard();
    expect(b).toHaveLength(20);
    for (const row of b) {
      expect(row).toHaveLength(10);
      expect(row.every((c) => c === null)).toBe(true);
    }
  });

  it('has 7 kinds, each rotation with exactly 4 distinct cells', () => {
    expect(PIECE_KINDS).toHaveLength(7);
    for (const k of PIECE_KINDS) {
      expect(PIECES[k].rotations).toHaveLength(4);
      for (const r of PIECES[k].rotations) {
        expect(new Set(r.map((c) => `${c.x},${c.y}`)).size).toBe(4);
      }
    }
  });

  it('uses original names and colours', () => {
    const names = PIECE_KINDS.map((k) => PIECES[k].name);
    expect(names).toEqual(['Bar', 'Block', 'Tee', 'Hook-L', 'Hook-R', 'Step-S', 'Step-Z']);
    const colours = PIECE_KINDS.map((k) => PIECES[k].color);
    expect(new Set(colours).size).toBe(7);
    const commercial = ['#00f0f0', '#f0f000', '#a000f0', '#00f000', '#f00000', '#0000f0', '#f0a000'];
    for (const c of colours) expect(commercial).not.toContain(c.toLowerCase());
  });
});

describe('R-05 collision, merge and clearing', () => {
  it('collides with walls, floor and locked cells', () => {
    const b = createBoard();
    b[5][5] = 'bar';
    expect(collides(b, [{ x: -1, y: 0 }])).toBe(true);
    expect(collides(b, [{ x: 10, y: 0 }])).toBe(true);
    expect(collides(b, [{ x: 0, y: 20 }])).toBe(true);
    expect(collides(b, [{ x: 5, y: 5 }])).toBe(true);
    expect(collides(b, [{ x: 4, y: 5 }])).toBe(false);
  });

  it('merge writes 4 cells with the piece colour key', () => {
    const cells = [{ x: 0, y: 19 }, { x: 1, y: 19 }, { x: 2, y: 19 }, { x: 3, y: 19 }];
    const b = mergePiece(createBoard(), cells, 'bar');
    expect(b.flat().filter((c) => c === 'bar')).toHaveLength(4);
  });

  it('clears a single row and shifts rows above down by one', () => {
    const b = createBoard();
    b[18][2] = 'block';
    fullRow(b, 19);
    const r = clearFullRows(b);
    expect(r.cleared).toBe(1);
    expect(r.board[19][2]).toBe('block');
    expect(r.board).toHaveLength(BOARD_HEIGHT);
    expect(r.board[0].every((c) => c === null)).toBe(true);
  });

  it('clears four rows at once', () => {
    const b = createBoard();
    for (let y = 16; y < 20; y++) fullRow(b, y);
    const r = clearFullRows(b);
    expect(r.cleared).toBe(4);
    expect(r.board.flat().every((c) => c === null)).toBe(true);
    expect(r.board).toHaveLength(20);
  });

  it('clears non-adjacent rows 17 and 19 and moves the rest correctly', () => {
    const b = createBoard();
    b[16][1] = 'hookL';
    b[18][0] = 'hookR';
    fullRow(b, 17);
    fullRow(b, 19);
    const r = clearFullRows(b);
    expect(r.cleared).toBe(2);
    expect(r.board[19][0]).toBe('hookR');
    expect(r.board[18][1]).toBe('hookL');
    expect(r.board.flat().filter((c) => c !== null)).toHaveLength(2);
    expect(r.board).toHaveLength(20);
  });

  it('a lock that clears nothing leaves rows unchanged', () => {
    const b = createBoard();
    b[19][0] = 'tee';
    b[10][4] = 'bar';
    const r = clearFullRows(b);
    expect(r.cleared).toBe(0);
    expect(r.board).toEqual(b);
  });
});
