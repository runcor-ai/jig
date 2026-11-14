import { describe, expect, it } from 'vitest';
import * as L from '../logic';

type Mv = [number, number] | 'pass';
const playAll = (g: L.Game, moves: Mv[]) => moves.reduce((x, m) => (m === 'pass' ? L.pass(x) : L.play(x, m[0], m[1])), g);

describe('GOCAP', () => {
  it('H1 a new board is empty with black to move; a lone stone has 4 liberties, 2 in a corner', () => {
    const g = L.newGame(5);
    expect(g.board.length).toBe(5);
    expect(g.board.flat().every((s) => s === null)).toBe(true);
    expect(g.turn).toBe('B');
    expect(g.captured).toEqual({ B: 0, W: 0 });
    expect(L.liberties(L.play(g, 2, 2), 2, 2)).toBe(4);
    expect(L.liberties(L.play(g, 0, 0), 0, 0)).toBe(2);
    expect(L.liberties(g, 2, 2)).toBe(0);
  });
  it('H2 joined stones form one group and share their liberties', () => {
    const g = playAll(L.newGame(5), [[2, 2], 'pass', [2, 3]]);
    expect(L.groupAt(g, 2, 3)).toEqual([[2, 2], [2, 3]]);
    expect(L.liberties(g, 2, 2)).toBe(6);
    expect(L.play(g, 2, 2)).toBe(g);
  });
  it('H3 a surrounded stone is captured and counted', () => {
    const g = playAll(L.newGame(5), [[0, 1], [1, 1], [1, 0], 'pass', [2, 1], 'pass', [1, 2]]);
    expect(g.board[1][1]).toBeNull();
    expect(g.captured).toEqual({ B: 1, W: 0 });
    expect(g.turn).toBe('W');
  });
  it('H4 suicide is not allowed', () => {
    const g = playAll(L.newGame(5), [[0, 1], 'pass', [1, 0]]);
    expect(g.turn).toBe('W');
    expect(L.play(g, 0, 0)).toBe(g);
  });
  it('H5 a move with no liberties is allowed when it captures', () => {
    const g = playAll(L.newGame(5), [[0, 1], [0, 2], [1, 0], [1, 3], [2, 1], [2, 2], 'pass', [1, 1]]);
    const h = L.play(g, 1, 2);
    expect(h.board[1][1]).toBeNull();
    expect(h.board[1][2]).toBe('B');
    expect(h.captured.B).toBe(1);
  });
  it('H6 ko: the immediate recapture is not allowed, but it is after a move elsewhere', () => {
    const g = playAll(L.newGame(5), [[0, 1], [0, 2], [1, 0], [1, 3], [2, 1], [2, 2], 'pass', [1, 1], [1, 2]]);
    expect(g.turn).toBe('W');
    expect(L.play(g, 1, 1)).toBe(g);
    const later = playAll(g, [[4, 4], [4, 0], [1, 1]]);
    expect(later.board[1][2]).toBeNull();
    expect(later.board[1][1]).toBe('W');
    expect(later.captured).toEqual({ B: 1, W: 1 });
  });
});
