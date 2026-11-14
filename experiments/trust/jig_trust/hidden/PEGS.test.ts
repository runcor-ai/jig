import { describe, expect, it } from 'vitest';
import * as L from '../logic';

describe('PEGS', () => {
  it('H1 the standard board is a cross of 33 holes with 32 pegs', () => {
    const b = L.standard();
    expect(b.length).toBe(7);
    expect(b[0][0]).toBe('off');
    expect(b[0][2]).toBe('peg');
    expect(b[3][0]).toBe('peg');
    expect(b[3][3]).toBe('empty');
    expect(b.flat().filter((c) => c !== 'off').length).toBe(33);
    expect(L.pegsLeft(b)).toBe(32);
  });
  it('H2 fromStrings reads pegs, empty holes and off-board cells', () => {
    const b = L.fromStrings(['o.', ' o']);
    expect(b).toEqual([['peg', 'empty'], ['off', 'peg']]);
  });
  it('H3 canJump needs a peg, a peg to jump over, and an empty hole two cells away in a line', () => {
    const b = L.standard();
    expect(L.canJump(b, 1, 3, 3, 3)).toBe(true);
    expect(L.canJump(b, 3, 1, 3, 3)).toBe(true);
    expect(L.canJump(b, 2, 2, 3, 3)).toBe(false);      // diagonal
    expect(L.canJump(b, 3, 2, 3, 3)).toBe(false);      // only one cell away
    expect(L.canJump(b, 1, 3, 2, 3)).toBe(false);      // target has a peg
  });
  it('H4 jump moves the peg and removes the jumped one, keeping the old board', () => {
    const b = L.standard();
    const j = L.jump(b, 1, 3, 3, 3);
    expect(j[1][3]).toBe('empty');
    expect(j[2][3]).toBe('empty');
    expect(j[3][3]).toBe('peg');
    expect(L.pegsLeft(j)).toBe(31);
    expect(b[3][3]).toBe('empty');
  });
  it('H5 an illegal jump returns the same board object', () => {
    const b = L.standard();
    expect(L.jump(b, 2, 2, 3, 3)).toBe(b);
    expect(L.jump(b, 0, 0, 0, 2)).toBe(b);
  });
  it('H6 hasMoves is false when no jump is possible', () => {
    expect(L.hasMoves(L.standard())).toBe(true);
    expect(L.hasMoves(L.fromStrings(['o.o', '...', 'o.o']))).toBe(false);
    expect(L.hasMoves(L.fromStrings(['oo.']))).toBe(true);
  });
});
