import { describe, expect, it } from 'vitest';
import * as L from '../logic';

const play = (g: L.Game, ms: [number, number][]) => ms.reduce((x, [f, t]) => L.move(x, f, t), g);

describe('HANOI', () => {
  it('H1 newGame stacks every disc on the first peg, largest at the bottom', () => {
    expect(L.newGame(3)).toEqual({ pegs: [[3, 2, 1], [], []], moves: 0 });
  });
  it('H2 canMove allows a smaller disc onto a larger one or an empty peg', () => {
    const g = L.newGame(3);
    expect(L.canMove(g, 0, 1)).toBe(true);
    const h = L.move(g, 0, 1);
    expect(L.canMove(h, 0, 1)).toBe(false);
    expect(L.canMove(h, 1, 0)).toBe(true);
    expect(L.canMove(h, 2, 0)).toBe(false);
  });
  it('H3 bad pegs and same-peg moves are not allowed', () => {
    const g = L.newGame(3);
    expect(L.canMove(g, 0, 0)).toBe(false);
    expect(L.canMove(g, 0, 3)).toBe(false);
    expect(L.canMove(g, -1, 1)).toBe(false);
  });
  it('H4 move moves the top disc, counts it, and keeps the old game', () => {
    const g = L.newGame(3);
    const h = L.move(g, 0, 2);
    expect(h).toEqual({ pegs: [[3, 2], [], [1]], moves: 1 });
    expect(g.pegs).toEqual([[3, 2, 1], [], []]);
    expect(L.move(h, 0, 2)).toBe(h);
  });
  it('H5 the shortest solution of three discs solves the puzzle in seven moves', () => {
    const g = play(L.newGame(3), [[0, 2], [0, 1], [2, 1], [0, 2], [1, 0], [1, 2], [0, 2]]);
    expect(L.isSolved(g)).toBe(true);
    expect(g.moves).toBe(7);
    expect(L.isSolved(L.newGame(3))).toBe(false);
  });
  it('H6 fewestMoves is two to the n, minus one', () => {
    expect(L.fewestMoves(1)).toBe(1);
    expect(L.fewestMoves(3)).toBe(7);
    expect(L.fewestMoves(7)).toBe(127);
  });
});
