import { describe, expect, it } from 'vitest';
import * as L from '../logic';

const gen = (lines: string[]) => L.toStrings(L.step(L.fromStrings(lines)));

describe('LIFE', () => {
  it('H1 fromStrings and toStrings round-trip', () => {
    const lines = ['.#.', '##.', '...'];
    const c = L.fromStrings(lines);
    expect(c[0][1]).toBe(true);
    expect(c[0][0]).toBe(false);
    expect(c[1][0]).toBe(true);
    expect(L.toStrings(c)).toEqual(lines);
  });
  it('H2 neighbors counts live cells around a cell, treating the outside as dead', () => {
    const c = L.fromStrings(['###', '#.#', '###']);
    expect(L.neighbors(c, 1, 1)).toBe(8);
    expect(L.neighbors(c, 0, 0)).toBe(2);
    expect(L.neighbors(c, 0, 1)).toBe(4);
  });
  it('H3 a blinker oscillates', () => {
    expect(gen(['.....', '.....', '.###.', '.....', '.....'])).toEqual(['.....', '..#..', '..#..', '..#..', '.....']);
    expect(gen(['.....', '..#..', '..#..', '..#..', '.....'])).toEqual(['.....', '.....', '.###.', '.....', '.....']);
  });
  it('H4 a block is stable and a lone cell dies', () => {
    expect(gen(['....', '.##.', '.##.', '....'])).toEqual(['....', '.##.', '.##.', '....']);
    expect(gen(['...', '.#.', '...'])).toEqual(['...', '...', '...']);
  });
  it('H5 edges do not wrap around', () => {
    // a blinker against the left edge loses the cells that would be off the grid
    expect(gen(['#..', '#..', '#..'])).toEqual(['...', '##.', '...']);
  });
  it('H6 step returns a new grid and does not change its input', () => {
    const c = L.fromStrings(['.#.', '.#.', '.#.']);
    const before = L.toStrings(c);
    const next = L.step(c);
    expect(next).not.toBe(c);
    expect(L.toStrings(c)).toEqual(before);
    expect(next.length).toBe(3);
    expect(next[0].length).toBe(3);
  });
});
