import { describe, expect, it } from 'vitest';
import * as L from '../logic';

const A = { name: 'a', row: 0, col: 0, length: 3, horizontal: true };
const B = { name: 'b', row: 2, col: 4, length: 2, horizontal: false };

describe('BATTLE', () => {
  it('H1 cells go right for horizontal ships and down for vertical ones', () => {
    expect(L.cells(A)).toEqual([[0, 0], [0, 1], [0, 2]]);
    expect(L.cells(B)).toEqual([[2, 4], [3, 4]]);
  });
  it('H2 canPlace rejects ships outside the grid or overlapping another', () => {
    expect(L.canPlace(5, [], A)).toBe(true);
    expect(L.canPlace(5, [], { ...A, col: 3 })).toBe(false);
    expect(L.canPlace(5, [], { ...B, row: 4 })).toBe(false);
    expect(L.canPlace(5, [A], { name: 'c', row: 0, col: 2, length: 2, horizontal: false })).toBe(false);
    expect(L.canPlace(5, [A], { name: 'c', row: 1, col: 0, length: 3, horizontal: true })).toBe(true);
  });
  it('H3 fire records shots without changing the old game', () => {
    const g0 = L.newGame(5, [A, B]);
    expect(g0.shots).toEqual([]);
    const g1 = L.fire(g0, 0, 0);
    expect(g1.shots).toEqual([[0, 0]]);
    expect(g0.shots).toEqual([]);
  });
  it('H4 repeated or outside shots return the same game object', () => {
    const g = L.fire(L.newGame(5, [A, B]), 0, 0);
    expect(L.fire(g, 0, 0)).toBe(g);
    expect(L.fire(g, 5, 0)).toBe(g);
    expect(L.fire(g, -1, 2)).toBe(g);
  });
  it('H5 result tells unknown, miss, hit and sunk apart', () => {
    let g = L.newGame(5, [A, B]);
    expect(L.result(g, 4, 4)).toBe('unknown');
    g = L.fire(g, 4, 4);
    expect(L.result(g, 4, 4)).toBe('miss');
    g = L.fire(g, 2, 4);
    expect(L.result(g, 2, 4)).toBe('hit');
    g = L.fire(g, 3, 4);
    expect(L.result(g, 2, 4)).toBe('sunk');
    expect(L.result(g, 3, 4)).toBe('sunk');
  });
  it('H6 the game is won when every ship cell is shot, and no shots after that', () => {
    let g = L.newGame(5, [A, B]);
    for (const [r, c] of [[0, 0], [0, 1], [0, 2], [2, 4]] as [number, number][]) g = L.fire(g, r, c);
    expect(L.isWon(g)).toBe(false);
    g = L.fire(g, 3, 4);
    expect(L.isWon(g)).toBe(true);
    expect(L.fire(g, 4, 0)).toBe(g);
  });
});
