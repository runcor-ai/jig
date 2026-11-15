import { describe, expect, it } from 'vitest';
import { COLS, KINDS, ROTATIONS, pieceCells, randomPiece, rotatePiece, spawnPiece } from './pieces';

describe('pieces (R-01, R-02)', () => {
  it('has 7 kinds with 4 cells in every rotation', () => {
    expect(KINDS).toHaveLength(7);
    for (const k of KINDS) {
      expect(ROTATIONS[k]).toHaveLength(4);
      for (const m of ROTATIONS[k]) expect(m.flat().filter(Boolean)).toHaveLength(4);
    }
  });

  it('four rotations return to the original', () => {
    for (const k of KINDS) {
      let p = spawnPiece(k);
      const start = pieceCells(p);
      for (let i = 0; i < 4; i++) p = rotatePiece(p);
      expect(pieceCells(p)).toEqual(start);
    }
  });

  it('O rotation changes nothing visible', () => {
    const p = spawnPiece('O');
    expect(pieceCells(rotatePiece(p))).toEqual(pieceCells(p));
  });

  it('spawns centred at the top', () => {
    for (const k of KINDS) {
      const xs = pieceCells(spawnPiece(k)).map(([x]) => x);
      const ys = pieceCells(spawnPiece(k)).map(([, y]) => y);
      expect(Math.min(...ys)).toBeLessThanOrEqual(1);
      const left = Math.min(...xs);
      const right = COLS - 1 - Math.max(...xs);
      expect(Math.abs(left - right)).toBeLessThanOrEqual(1);
    }
  });

  it('randomPiece follows rng deterministically', () => {
    expect(randomPiece(() => 0)).toBe('I');
    expect(randomPiece(() => 0.999)).toBe('L');
    const seq = [0.1, 0.3, 0.5, 0.7];
    const run = () => {
      let i = 0;
      return Array.from({ length: 4 }, () => randomPiece(() => seq[i++]));
    };
    expect(run()).toEqual(run());
    expect(run()).toEqual(['I', 'T', 'S', 'Z']);
  });

  it('every kind appears with Math.random', () => {
    const seen = new Set<string>();
    for (let i = 0; i < 2000; i++) seen.add(randomPiece(Math.random));
    expect(seen.size).toBe(7);
  });
});
