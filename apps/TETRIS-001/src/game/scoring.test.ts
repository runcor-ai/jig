import { describe, expect, it } from 'vitest';
import { dropInterval, levelForRows, scoreForLines } from './scoring';

describe('R-06 scoring and levels', () => {
  it('scoreForLines(0..4)', () => {
    expect([0, 1, 2, 3, 4].map(scoreForLines)).toEqual([0, 100, 300, 500, 800]);
  });
  it('level boundaries', () => {
    expect(levelForRows(0)).toBe(1);
    expect(levelForRows(9)).toBe(1);
    expect(levelForRows(10)).toBe(2);
    expect(levelForRows(19)).toBe(2);
    expect(levelForRows(20)).toBe(3);
    expect(levelForRows(11)).toBe(2);
  });
});

describe('R-07 drop interval', () => {
  it('known values', () => {
    expect(dropInterval(1)).toBe(1000);
    expect(dropInterval(2)).toBe(920);
    expect(dropInterval(5)).toBe(680);
  });
  it('strictly decreases until the floor, never below 100', () => {
    for (let l = 1; l < 11; l++) expect(dropInterval(l + 1)).toBeLessThan(dropInterval(l));
    for (let l = 1; l < 100; l++) expect(dropInterval(l)).toBeGreaterThanOrEqual(100);
    expect(dropInterval(50)).toBe(100);
  });
});
