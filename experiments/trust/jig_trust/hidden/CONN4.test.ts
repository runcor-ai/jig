import { describe, expect, it } from 'vitest';
import * as L from '../logic';

const dropAll = (cols: number[], g = L.newGame()) => cols.reduce((x, c) => L.drop(x, c), g);

describe('CONN4', () => {
  it('H1 newGame is an empty 7 x 6 grid with red to move, and sizes can be given', () => {
    const g = L.newGame();
    expect(g.cols).toBe(7);
    expect(g.rows).toBe(6);
    expect(g.grid.length).toBe(6);
    expect(g.grid.every((r) => r.length === 7 && r.every((c) => c === null))).toBe(true);
    expect(g.turn).toBe('R');
    const s = L.newGame(5, 4);
    expect(s.grid.length).toBe(4);
    expect(s.grid[0].length).toBe(5);
  });
  it('H2 discs fall to the lowest empty row, turns alternate, and the old game is unchanged', () => {
    const g0 = L.newGame();
    const g1 = L.drop(g0, 3);
    expect(g1.grid[5][3]).toBe('R');
    expect(g1.turn).toBe('Y');
    const g2 = L.drop(g1, 3);
    expect(g2.grid[4][3]).toBe('Y');
    expect(g0.grid[5][3]).toBeNull();
  });
  it('H3 a full or out-of-range column returns the same game object', () => {
    const full = dropAll([0, 0, 0, 0, 0, 0]);
    expect(L.drop(full, 0)).toBe(full);
    expect(L.drop(full, 7)).toBe(full);
    expect(L.drop(full, -1)).toBe(full);
  });
  it('H4 four across and four down win', () => {
    expect(L.winner(dropAll([0, 0, 1, 1, 2, 2, 3]))).toBe('R');
    expect(L.winner(dropAll([0, 1, 0, 1, 0, 1, 6, 1]))).toBe('Y');
  });
  it('H5 both diagonals win', () => {
    // rising diagonal for R: (5,0) (4,1) (3,2) (2,3)
    expect(L.winner(dropAll([0, 1, 1, 2, 2, 3, 2, 3, 3, 6, 3]))).toBe('R');
    // falling diagonal for R: (2,0) (3,1) (4,2) (5,3)
    expect(L.winner(dropAll([3, 2, 2, 1, 1, 0, 1, 0, 0, 6, 0]))).toBe('R');
  });
  it('H6 no drops after a win, and a full grid with no line is a draw', () => {
    const won = dropAll([0, 0, 1, 1, 2, 2, 3]);
    expect(L.drop(won, 5)).toBe(won);
    // 2 columns x 2 rows can never hold four in a line
    const tiny = dropAll([0, 0, 1, 1], L.newGame(2, 2));
    expect(L.winner(tiny)).toBe('draw');
  });
});
