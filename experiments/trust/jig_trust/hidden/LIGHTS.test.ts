import { describe, expect, it } from 'vitest';
import * as L from '../logic';

const ons = (b: boolean[][]) => b.flatMap((r, i) => r.map((v, j) => (v ? `${i},${j}` : ''))).filter(Boolean).sort();

describe('LIGHTS', () => {
  it('H1 create sets the given lights on and the rest off', () => {
    const b = L.create(3, [[0, 0], [2, 1]]);
    expect(b.length).toBe(3);
    expect(b.every((r) => r.length === 3)).toBe(true);
    expect(ons(b)).toEqual(['0,0', '2,1']);
    expect(L.countOn(b)).toBe(2);
  });
  it('H2 pressing the centre toggles a cross of five', () => {
    expect(ons(L.press(L.create(5, []), 2, 2))).toEqual(['1,2', '2,1', '2,2', '2,3', '3,2']);
  });
  it('H3 pressing a corner toggles only the lights that exist', () => {
    expect(ons(L.press(L.create(5, []), 0, 0))).toEqual(['0,0', '0,1', '1,0']);
    expect(ons(L.press(L.create(5, []), 4, 2))).toEqual(['3,2', '4,1', '4,2', '4,3']);
  });
  it('H4 pressing toggles lights that were already on off again', () => {
    const b = L.create(3, [[1, 1], [0, 1]]);
    expect(ons(L.press(b, 1, 1))).toEqual(['1,0', '1,2', '2,1']);
  });
  it('H5 press returns a new board, keeps the old one, and ignores presses outside', () => {
    const b = L.create(3, []);
    const p = L.press(b, 1, 1);
    expect(p).not.toBe(b);
    expect(L.countOn(b)).toBe(0);
    expect(L.press(b, 3, 0)).toBe(b);
    expect(L.press(b, -1, 1)).toBe(b);
  });
  it('H6 pressing the same light twice solves a board that started solved', () => {
    const b = L.create(5, []);
    expect(L.isSolved(b)).toBe(true);
    const once = L.press(b, 1, 3);
    expect(L.isSolved(once)).toBe(false);
    expect(L.countOn(once)).toBe(5);
    expect(L.isSolved(L.press(once, 1, 3))).toBe(true);
  });
});
