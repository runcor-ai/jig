import { describe, expect, it } from 'vitest';
import * as L from '../logic';

const count = (g: boolean[][]) => g.flat().filter(Boolean).length;

describe('MINES', () => {
  it('H1 createBoard places mines at [x, y] with nothing revealed or flagged', () => {
    const b = L.createBoard(4, 3, [[3, 0], [0, 2]]);
    expect(b.width).toBe(4);
    expect(b.height).toBe(3);
    expect(b.mines[0][3]).toBe(true);
    expect(b.mines[2][0]).toBe(true);
    expect(count(b.mines)).toBe(2);
    expect(count(b.revealed)).toBe(0);
    expect(count(b.flagged)).toBe(0);
    expect(L.status(b)).toBe('playing');
  });
  it('H2 adjacent counts the eight neighbours, including at edges', () => {
    const b = L.createBoard(3, 3, [[0, 0], [2, 0], [1, 2]]);
    expect(L.adjacent(b, 1, 1)).toBe(3);
    expect(L.adjacent(b, 1, 0)).toBe(2);
    expect(L.adjacent(b, 0, 2)).toBe(1);
  });
  it('H3 revealing a numbered cell reveals only that cell and keeps the old board', () => {
    const b = L.createBoard(3, 3, [[0, 0]]);
    const r = L.reveal(b, 1, 1);
    expect(r.revealed[1][1]).toBe(true);
    expect(count(r.revealed)).toBe(1);
    expect(count(b.revealed)).toBe(0);
  });
  it('H4 revealing a zero cell flood-fills and can win the game', () => {
    const b = L.createBoard(4, 4, [[3, 3]]);
    const r = L.reveal(b, 0, 0);
    expect(count(r.revealed)).toBe(15);
    expect(r.revealed[3][3]).toBe(false);
    expect(L.status(r)).toBe('won');
  });
  it('H5 revealing a mine loses, and nothing changes after that', () => {
    const b = L.createBoard(3, 3, [[2, 2]]);
    const lost = L.reveal(b, 2, 2);
    expect(L.status(lost)).toBe('lost');
    expect(L.reveal(lost, 0, 0)).toBe(lost);
  });
  it('H6 flags block reveals, and illegal actions return the same board', () => {
    const b = L.createBoard(3, 3, [[2, 2]]);
    const f = L.toggleFlag(b, 0, 0);
    expect(f.flagged[0][0]).toBe(true);
    expect(L.reveal(f, 0, 0)).toBe(f);
    expect(L.toggleFlag(f, 0, 0).flagged[0][0]).toBe(false);
    expect(L.reveal(b, 5, 5)).toBe(b);
    const r = L.reveal(b, 1, 1);
    expect(L.toggleFlag(r, 1, 1)).toBe(r);
  });
});
