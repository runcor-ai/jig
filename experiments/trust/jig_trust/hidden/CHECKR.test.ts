import { describe, expect, it } from 'vitest';
import * as L from '../logic';

const empty = (): L.Piece[][] => Array.from({ length: 8 }, () => Array(8).fill(null));
const paths = (g: L.Game) => L.legalMoves(g).map((m) => JSON.stringify(m.path)).sort();

describe('CHECKR', () => {
  it('H1 newGame has 12 men each on the dark squares, black to move', () => {
    const g = L.newGame();
    const flat = g.board.flatMap((row, r) => row.map((p, c) => ({ p, r, c })));
    expect(flat.filter((x) => x.p === 'b').length).toBe(12);
    expect(flat.filter((x) => x.p === 'w').length).toBe(12);
    expect(flat.filter((x) => x.p).every((x) => (x.r + x.c) % 2 === 1)).toBe(true);
    expect(flat.filter((x) => x.p === 'b').every((x) => x.r <= 2)).toBe(true);
    expect(g.turn).toBe('b');
  });
  it('H2 black has seven opening moves', () => {
    expect(paths(L.newGame())).toEqual([
      '[[2,1],[3,0]]', '[[2,1],[3,2]]', '[[2,3],[3,2]]', '[[2,3],[3,4]]', '[[2,5],[3,4]]', '[[2,5],[3,6]]',
      '[[2,7],[3,6]]',
    ].sort());
  });
  it('H3 a simple move updates the board and passes the turn; an illegal move returns the same game', () => {
    const g0 = L.newGame();
    const g1 = L.play(g0, { path: [[2, 1], [3, 0]] });
    expect(g1.board[3][0]).toBe('b');
    expect(g1.board[2][1]).toBeNull();
    expect(g1.turn).toBe('w');
    expect(g0.board[2][1]).toBe('b');
    expect(L.play(g0, { path: [[2, 1], [4, 3]] })).toBe(g0);
    expect(L.play(g0, { path: [[5, 0], [4, 1]] })).toBe(g0);
  });
  it('H4 capturing is compulsory', () => {
    const board = empty();
    board[2][1] = 'b'; board[3][2] = 'w'; board[2][5] = 'b'; board[7][0] = 'w';
    const g = { board, turn: 'b' as const };
    expect(paths(g)).toEqual(['[[2,1],[4,3]]']);
    const after = L.play(g, { path: [[2, 1], [4, 3]] });
    expect(after.board[3][2]).toBeNull();
    expect(after.board[4][3]).toBe('b');
    expect(L.play(g, { path: [[2, 5], [3, 6]] })).toBe(g);
  });
  it('H5 a capture must continue while the piece can jump again', () => {
    const board = empty();
    board[0][1] = 'b'; board[1][2] = 'w'; board[3][4] = 'w'; board[7][0] = 'w';
    const g = { board, turn: 'b' as const };
    expect(paths(g)).toEqual(['[[0,1],[2,3],[4,5]]']);
    const after = L.play(g, { path: [[0, 1], [2, 3], [4, 5]] });
    expect(after.board[1][2]).toBeNull();
    expect(after.board[3][4]).toBeNull();
    expect(after.board[4][5]).toBe('b');
    expect(L.play(g, { path: [[0, 1], [2, 3]] })).toBe(g);
  });
  it('H6 a man reaching the far row is crowned, and a king moves both ways', () => {
    const board = empty();
    board[6][1] = 'b'; board[0][7] = 'w';
    const crowned = L.play({ board, turn: 'b' }, { path: [[6, 1], [7, 0]] });
    expect(crowned.board[7][0]).toBe('B');
    const kb = empty();
    kb[4][3] = 'B'; kb[0][7] = 'w';
    const moves = paths({ board: kb, turn: 'b' }).filter((p) => p.startsWith('[[4,3]'));
    expect(moves).toEqual(['[[4,3],[3,2]]', '[[4,3],[3,4]]', '[[4,3],[5,2]]', '[[4,3],[5,4]]']);
  });
});
