import { describe, expect, it } from 'vitest';
import * as L from '../logic';

describe('CHESS', () => {
  it('H1 knights jump, from a corner and from the centre', () => {
    const b = L.parse(['....k...', '........', '........', '........', '...N....', '........', '........', 'N...K...']);
    expect(L.moves(b, 'a1')).toEqual(['b3', 'c2']);
    expect(L.moves(b, 'd4')).toEqual(['b3', 'b5', 'c2', 'c6', 'e2', 'e6', 'f3', 'f5']);
    expect(L.moves(b, 'c3')).toEqual([]);
  });
  it('H2 sliding pieces stop at their own pieces and capture the first enemy piece', () => {
    const b = L.parse(['....k...', '........', '........', '........', '........', 'P.......', '........', 'R..n...K']);
    expect(L.moves(b, 'a1')).toEqual(['a2', 'b1', 'c1', 'd1']);
  });
  it('H3 pawns move forward one or two from the start, capture diagonally, and are blocked', () => {
    const b = L.parse(['k.......', '........', '........', '........', '........', '...n...p', '....P..P', 'K.......']);
    expect(L.moves(b, 'e2')).toEqual(['d3', 'e3', 'e4']);
    expect(L.moves(b, 'h2')).toEqual([]);
    const bl = L.parse(['k.......', '...p....', '........', '........', '........', '........', '........', 'K.......']);
    expect(L.moves(bl, 'd7')).toEqual(['d5', 'd6']);
  });
  it('H4 inCheck sees an attack along an open line, and a blocked line is not check', () => {
    const open = L.parse(['....r..k', '........', '........', '........', '........', '........', '........', '....K...']);
    expect(L.inCheck(open, 'w')).toBe(true);
    expect(L.inCheck(open, 'b')).toBe(false);
    const blocked = L.parse(['....r..k', '........', '........', '........', '....N...', '........', '........', '....K...']);
    expect(L.inCheck(blocked, 'w')).toBe(false);
  });
  it('H5 a pinned piece may only move along the pin, and a king may not walk into attack', () => {
    const bishop = L.parse(['....r..k', '........', '........', '........', '........', '........', '....B...', '....K...']);
    expect(L.moves(bishop, 'e2')).toEqual([]);
    const rook = L.parse(['....r..k', '........', '........', '........', '........', '........', '....R...', '....K...']);
    expect(L.moves(rook, 'e2')).toEqual(['e3', 'e4', 'e5', 'e6', 'e7', 'e8']);
    const king = L.parse(['...r...k', '........', '........', '........', '........', '........', '........', '....K...']);
    expect(L.moves(king, 'e1')).toEqual(['e2', 'f1', 'f2']);
  });
  it('H6 checkmate needs check and no legal move', () => {
    const mate = L.parse(['....R.k.', '.....ppp', '........', '........', '........', '........', '........', 'K.......']);
    expect(L.inCheck(mate, 'b')).toBe(true);
    expect(L.isCheckmate(mate, 'b')).toBe(true);
    const escape = L.parse(['....R.k.', '.....pp.', '........', '........', '........', '........', '........', 'K.......']);
    expect(L.inCheck(escape, 'b')).toBe(true);
    expect(L.isCheckmate(escape, 'b')).toBe(false);
    expect(L.isCheckmate(mate, 'w')).toBe(false);
  });
});
