import { describe, expect, it } from 'vitest';
import { gravityMs, levelForRows, scoreForLines } from './scoring';

describe('scoring (R-07, R-08)', () => {
  it('score table', () => {
    expect([0, 1, 2, 3, 4].map(scoreForLines)).toEqual([0, 100, 300, 500, 800]);
  });
  it('levelForRows', () => {
    expect(levelForRows(0)).toBe(1);
    expect(levelForRows(9)).toBe(1);
    expect(levelForRows(10)).toBe(2);
    expect(levelForRows(25)).toBe(3);
  });
  it('gravityMs floor and decrease', () => {
    expect(gravityMs(1)).toBe(1000);
    expect(gravityMs(50)).toBe(100);
    for (let l = 1; l < 9; l++) expect(gravityMs(l + 1)).toBeLessThan(gravityMs(l));
  });
});
