import { describe, expect, it } from 'vitest';
import * as L from '../logic';

describe('G2048', () => {
  it('H1 slideRow slides tiles left past empty cells', () => {
    expect(L.slideRow([0, 2, 0, 4])).toEqual({ row: [2, 4, 0, 0], score: 0 });
    expect(L.slideRow([0, 0, 0, 0])).toEqual({ row: [0, 0, 0, 0], score: 0 });
  });
  it('H2 slideRow merges equal tiles once, nearest the edge first', () => {
    expect(L.slideRow([2, 2, 0, 0])).toEqual({ row: [4, 0, 0, 0], score: 4 });
    expect(L.slideRow([2, 2, 2, 0])).toEqual({ row: [4, 2, 0, 0], score: 4 });
    expect(L.slideRow([4, 4, 4, 4])).toEqual({ row: [8, 8, 0, 0], score: 16 });
    expect(L.slideRow([4, 4, 8, 0])).toEqual({ row: [8, 8, 0, 0], score: 8 });
  });
  it('H3 move right and left', () => {
    const g = [[2, 2, 0, 0], [0, 0, 0, 0], [4, 0, 4, 2], [0, 0, 0, 0]];
    expect(L.move(g, 'right')).toEqual({ grid: [[0, 0, 0, 4], [0, 0, 0, 0], [0, 0, 8, 2], [0, 0, 0, 0]], score: 12, moved: true });
    expect(L.move(g, 'left').grid).toEqual([[4, 0, 0, 0], [0, 0, 0, 0], [8, 2, 0, 0], [0, 0, 0, 0]]);
  });
  it('H4 move up and down work on columns', () => {
    const g = [[2, 0, 0, 0], [2, 0, 0, 0], [0, 4, 0, 0], [2, 4, 0, 0]];
    expect(L.move(g, 'up')).toEqual({ grid: [[4, 8, 0, 0], [2, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], score: 12, moved: true });
    expect(L.move(g, 'down').grid).toEqual([[0, 0, 0, 0], [0, 0, 0, 0], [2, 0, 0, 0], [4, 8, 0, 0]]);
  });
  it('H5 a move that changes nothing reports moved false and leaves the input unchanged', () => {
    const g = [[2, 4, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]];
    const copy = g.map((r) => r.slice());
    const r = L.move(g, 'left');
    expect(r.moved).toBe(false);
    expect(r.score).toBe(0);
    expect(r.grid).toEqual(copy);
    L.move(g, 'right');
    expect(g).toEqual(copy);
  });
  it('H6 canMove is false only when no move can change the grid', () => {
    expect(L.canMove([[2, 4, 2, 4], [4, 2, 4, 2], [2, 4, 2, 4], [4, 2, 4, 2]])).toBe(false);
    expect(L.canMove([[2, 4, 2, 4], [4, 2, 4, 2], [2, 4, 2, 4], [4, 2, 4, 4]])).toBe(true);
    expect(L.canMove([[2, 4, 2, 4], [4, 2, 4, 2], [2, 4, 2, 4], [4, 2, 4, 0]])).toBe(true);
  });
});
