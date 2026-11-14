export type Board = boolean[][];

export function create(n: number, on: [number, number][]): Board {
  const b = Array.from({ length: n }, () => Array(n).fill(false));
  for (const [r, c] of on) b[r][c] = true;
  return b;
}

export function press(b: Board, row: number, col: number): Board {
  const n = b.length;
  const ok = (r: number, c: number) => r >= 0 && c >= 0 && r < n && c < b[r].length;
  if (!ok(row, col)) return b;
  const next = b.map((r) => r.slice());
  for (const [dr, dc] of [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]])
    if (ok(row + dr, col + dc)) next[row + dr][col + dc] = !next[row + dr][col + dc];
  return next;
}

export const countOn = (b: Board) => b.flat().filter(Boolean).length;
export const isSolved = (b: Board) => countOn(b) === 0;
