import { describe, expect, it } from 'vitest';
import * as L from '../logic';

describe('SLIDE', () => {
  it('H1 solved is 1 to 15 then the gap, and isSolved agrees', () => {
    expect(L.solved()).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 0]);
    expect(L.isSolved(L.solved())).toBe(true);
  });
  it('H2 movable lists the tiles next to the gap in a corner', () => {
    expect(L.movable(L.solved())).toEqual([12, 15]);
  });
  it('H3 movable in the middle has four tiles and does not wrap rows', () => {
    const b = [1, 2, 3, 4, 5, 0, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15];
    expect(L.movable(b)).toEqual([2, 5, 6, 9]);
    const edge = [1, 2, 3, 0, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15];
    expect(L.movable(edge)).toEqual([3, 7]);
  });
  it('H4 slide swaps the tile and the gap without changing the old board', () => {
    const s = L.solved();
    const b = L.slide(s, 15);
    expect(b).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 0, 15]);
    expect(s).toEqual(L.solved());
    expect(L.isSolved(b)).toBe(false);
  });
  it('H5 a tile that is not next to the gap returns the same board object', () => {
    const s = L.solved();
    expect(L.slide(s, 1)).toBe(s);
    expect(L.slide(s, 11)).toBe(s);
    expect(L.slide(s, 99)).toBe(s);
  });
  it('H6 sliding back restores the solved board', () => {
    const b = L.slide(L.slide(L.slide(L.solved(), 15), 11), 11);
    expect(L.isSolved(L.slide(b, 15))).toBe(true);
  });
});
