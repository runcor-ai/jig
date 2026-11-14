import { describe, expect, it } from 'vitest';
import * as L from '../logic';

const empty = (): (L.Disc | null)[][] => Array.from({ length: 8 }, () => Array(8).fill(null));

describe('REVERS', () => {
  it('H1 newGame has the four centre discs with black to move', () => {
    const g = L.newGame();
    expect(g.board[3][3]).toBe('W');
    expect(g.board[4][4]).toBe('W');
    expect(g.board[3][4]).toBe('B');
    expect(g.board[4][3]).toBe('B');
    expect(g.turn).toBe('B');
    expect(L.score(g)).toEqual({ B: 2, W: 2 });
  });
  it('H2 black has four legal opening moves, in row-then-column order', () => {
    expect(L.legalMoves(L.newGame())).toEqual([[2, 3], [3, 2], [4, 5], [5, 4]]);
  });
  it('H3 a move flips the bracketed disc, passes the turn, and keeps the old game', () => {
    const g0 = L.newGame();
    const g1 = L.play(g0, 2, 3);
    expect(g1.board[2][3]).toBe('B');
    expect(g1.board[3][3]).toBe('B');
    expect(L.score(g1)).toEqual({ B: 4, W: 1 });
    expect(g1.turn).toBe('W');
    expect(g0.board[3][3]).toBe('W');
  });
  it('H4 illegal moves return the same game object', () => {
    const g = L.newGame();
    expect(L.play(g, 0, 0)).toBe(g);      // flips nothing
    expect(L.play(g, 3, 3)).toBe(g);      // occupied
    expect(L.play(g, 8, 0)).toBe(g);      // outside
  });
  it('H5 one move flips lines in several directions at once', () => {
    const board = empty();
    board[4][0] = 'B'; board[4][1] = 'W'; board[4][2] = 'W';
    board[5][3] = 'W'; board[6][3] = 'B';
    board[5][4] = 'W'; board[6][5] = 'B';
    const g = L.play({ board, turn: 'B' }, 4, 3);
    expect(g.board[4][1]).toBe('B');
    expect(g.board[4][2]).toBe('B');
    expect(g.board[5][3]).toBe('B');
    expect(g.board[5][4]).toBe('B');
    expect(L.score(g)).toEqual({ B: 8, W: 0 });
  });
  it('H6 a player with no move passes, and the game ends when neither can move', () => {
    const board = empty();
    board[0][0] = 'B'; board[0][1] = 'W';
    board[7][7] = 'W'; board[7][6] = 'B'; board[7][5] = 'B';
    // black to move: (0,2) flips (0,1). Then white has (7,4) to flip the two blacks, so white moves next.
    const g1 = L.play({ board, turn: 'B' }, 0, 2);
    expect(g1.turn).toBe('W');
    const g2 = L.play(g1, 7, 4);
    expect(L.score(g2)).toEqual({ B: 3, W: 4 });
    // black has no move left and neither has white: the game is over
    expect(L.legalMoves(g2)).toEqual([]);
    expect(L.isOver(g2)).toBe(true);
  });
});
