import { describe, expect, it } from 'vitest';
import * as L from '../logic';

const playAll = (cells: number[]) => cells.reduce((g, c) => L.play(g, c), L.newGame());

describe('TICTAC', () => {
  it('H1 newGame starts empty with X to move', () => {
    const g = L.newGame();
    expect(g.board).toEqual([null, null, null, null, null, null, null, null, null]);
    expect(g.turn).toBe('X');
    expect(L.winner(g)).toBeNull();
  });
  it('H2 play places the mark, alternates turns and does not change the old game', () => {
    const g0 = L.newGame();
    const g1 = L.play(g0, 4);
    expect(g1.board[4]).toBe('X');
    expect(g1.turn).toBe('O');
    expect(g0.board[4]).toBeNull();
    const g2 = L.play(g1, 0);
    expect(g2.board[0]).toBe('O');
    expect(g2.turn).toBe('X');
  });
  it('H3 an illegal move returns the same game object', () => {
    const g1 = L.play(L.newGame(), 4);
    expect(L.play(g1, 4)).toBe(g1);
    expect(L.play(g1, 9)).toBe(g1);
    expect(L.play(g1, -1)).toBe(g1);
  });
  it('H4 detects a row, a column and a diagonal', () => {
    expect(L.winner(playAll([0, 3, 1, 4, 2]))).toBe('X');          // top row
    expect(L.winner(playAll([1, 0, 2, 3, 4, 6]))).toBe('O');       // left column
    expect(L.winner(playAll([0, 1, 4, 2, 8]))).toBe('X');          // diagonal
    expect(L.winner(playAll([2, 0, 4, 1, 6]))).toBe('X');          // anti-diagonal
  });
  it('H5 a full board with no line is a draw', () => {
    // X O X / X O O / O X X
    expect(L.winner(playAll([0, 1, 2, 4, 3, 5, 7, 6, 8]))).toBe('draw');
  });
  it('H6 no move is accepted after a win', () => {
    const won = playAll([0, 3, 1, 4, 2]);
    expect(L.play(won, 8)).toBe(won);
  });
});
