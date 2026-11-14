export type Cells = boolean[][];

export function neighbors(c: Cells, row: number, col: number): number {
  let n = 0;
  for (let dr = -1; dr <= 1; dr++) for (let dc = -1; dc <= 1; dc++) {
    if (!dr && !dc) continue;
    const r = row + dr, k = col + dc;
    if (r >= 0 && r < c.length && k >= 0 && k < c[r].length && c[r][k]) n++;
  }
  return n;
}

export function step(c: Cells): Cells {
  return c.map((line, r) => line.map((alive, k) => {
    const n = neighbors(c, r, k);
    return alive ? n === 2 || n === 3 : n === 3;
  }));
}

export const fromStrings = (lines: string[]): Cells => lines.map((l) => [...l].map((ch) => ch === '#'));
export const toStrings = (c: Cells): string[] => c.map((l) => l.map((a) => (a ? '#' : '.')).join(''));
