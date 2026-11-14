import { describe, expect, it } from 'vitest';
import * as L from '../logic';

const rep = (n: number, x: number) => Array(n).fill(x);

describe('BOWL', () => {
  it('H1 a gutter game and an all-ones game', () => {
    expect(L.score(rep(20, 0))).toBe(0);
    expect(L.score(rep(20, 1))).toBe(20);
  });
  it('H2 a spare scores the next roll as bonus', () => {
    expect(L.score([5, 5, 3, ...rep(17, 0)])).toBe(16);
  });
  it('H3 a strike scores the next two rolls as bonus', () => {
    expect(L.score([10, 3, 4, ...rep(16, 0)])).toBe(24);
  });
  it('H4 a perfect game is 300 and an all-spares game with a final 5 is 150', () => {
    expect(L.score(rep(12, 10))).toBe(300);
    expect(L.score(rep(21, 5))).toBe(150);
  });
  it('H5 frameScores gives running totals and null for frames not yet scoreable', () => {
    expect(L.frameScores([10, 3, 4])).toEqual([17, 24, null, null, null, null, null, null, null, null]);
    expect(L.frameScores([10])).toEqual(rep(10, null));
    expect(L.frameScores([3, 7])).toEqual(rep(10, null));
    expect(L.score([3, 7])).toBe(0);
  });
  it('H6 isComplete knows about the tenth-frame bonus rolls', () => {
    expect(L.isComplete(rep(20, 1))).toBe(true);
    expect(L.isComplete(rep(19, 1))).toBe(false);
    expect(L.isComplete([...rep(18, 0), 5, 5])).toBe(false);
    expect(L.isComplete([...rep(18, 0), 5, 5, 3])).toBe(true);
    expect(L.isComplete(rep(11, 10))).toBe(false);
    expect(L.isComplete(rep(12, 10))).toBe(true);
  });
});
