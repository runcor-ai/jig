import { describe, expect, it } from 'vitest';
import * as L from '../logic';

const SOLVED = '534678912672195348198342567859761423426853791713924856961537284287419635345286179';
const PUZZLE = '53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79';

describe('SUDOKU', () => {
  it('H1 parse reads digits row by row, with 0 or . as empty', () => {
    const g = L.parse(PUZZLE);
    expect(g.length).toBe(9);
    expect(g[0]).toEqual([5, 3, 0, 0, 7, 0, 0, 0, 0]);
    expect(g[8][8]).toBe(9);
    expect(L.parse(PUZZLE.replace(/\./g, '0'))).toEqual(g);
  });
  it('H2 a solved grid has no conflicts and is solved; a puzzle with gaps is not', () => {
    expect(L.conflicts(L.parse(SOLVED))).toEqual([]);
    expect(L.isSolved(L.parse(SOLVED))).toBe(true);
    expect(L.isSolved(L.parse(PUZZLE))).toBe(false);
  });
  it('H3 conflicts finds repeats in rows, columns and boxes', () => {
    const g = L.place(L.parse(PUZZLE), 0, 2, 5);           // a second 5 in row 0
    expect(L.conflicts(g)).toEqual([[0, 0], [0, 2]]);
    const h = L.place(L.parse(PUZZLE), 1, 1, 9);           // 9 again in row 1, column 1 and the top-left box
    expect(L.conflicts(h)).toEqual([[1, 1], [1, 4], [2, 1]]);
  });
  it('H4 candidates lists the digits still possible, and none for a filled cell', () => {
    const g = L.parse(PUZZLE);
    expect(L.candidates(g, 0, 2)).toEqual([1, 2, 4]);
    expect(L.candidates(g, 4, 4)).toEqual([5]);
    expect(L.candidates(g, 0, 0)).toEqual([]);
  });
  it('H5 place returns a new grid, can clear a cell, and keeps the old grid', () => {
    const g = L.parse(PUZZLE);
    const h = L.place(g, 0, 2, 4);
    expect(h[0][2]).toBe(4);
    expect(g[0][2]).toBe(0);
    expect(L.place(h, 0, 2, 0)[0][2]).toBe(0);
  });
  it('H6 out-of-range positions or digits return the same grid object', () => {
    const g = L.parse(PUZZLE);
    expect(L.place(g, 9, 0, 1)).toBe(g);
    expect(L.place(g, 0, -1, 1)).toBe(g);
    expect(L.place(g, 0, 2, 10)).toBe(g);
  });
});
