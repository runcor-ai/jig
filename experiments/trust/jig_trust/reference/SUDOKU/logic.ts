export type Grid = number[][];

export function parse(s: string): Grid {
  const d = [...s].map((ch) => (ch === '.' ? 0 : Number(ch)));
  return Array.from({ length: 9 }, (_, r) => d.slice(r * 9, r * 9 + 9));
}

function peers(r: number, c: number): [number, number][] {
  const out: [number, number][] = [];
  for (let i = 0; i < 9; i++) {
    if (i !== c) out.push([r, i]);
    if (i !== r) out.push([i, c]);
  }
  const br = r - (r % 3), bc = c - (c % 3);
  for (let i = br; i < br + 3; i++) for (let j = bc; j < bc + 3; j++) if (i !== r && j !== c) out.push([i, j]);
  return out;
}

export function conflicts(g: Grid): [number, number][] {
  const out: [number, number][] = [];
  for (let r = 0; r < 9; r++) for (let c = 0; c < 9; c++)
    if (g[r][c] && peers(r, c).some(([i, j]) => g[i][j] === g[r][c])) out.push([r, c]);
  return out;
}

export function candidates(g: Grid, r: number, c: number): number[] {
  if (g[r][c]) return [];
  const used = new Set(peers(r, c).map(([i, j]) => g[i][j]));
  return [1, 2, 3, 4, 5, 6, 7, 8, 9].filter((d) => !used.has(d));
}

export function place(g: Grid, r: number, c: number, d: number): Grid {
  if (![r, c].every((x) => Number.isInteger(x) && x >= 0 && x < 9) || !Number.isInteger(d) || d < 0 || d > 9) return g;
  const next = g.map((row) => row.slice());
  next[r][c] = d;
  return next;
}

export const isSolved = (g: Grid) => g.every((row) => row.every((v) => v > 0)) && conflicts(g).length === 0;
