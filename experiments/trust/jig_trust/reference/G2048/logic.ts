export type Grid = number[][];
export type Dir = 'left' | 'right' | 'up' | 'down';

export function slideRow(row: number[]): { row: number[]; score: number } {
  const tiles = row.filter((x) => x !== 0);
  const out: number[] = [];
  let score = 0;
  for (let i = 0; i < tiles.length; i++) {
    if (i + 1 < tiles.length && tiles[i] === tiles[i + 1]) {
      out.push(tiles[i] * 2);
      score += tiles[i] * 2;
      i++;
    } else out.push(tiles[i]);
  }
  while (out.length < row.length) out.push(0);
  return { row: out, score };
}

const transpose = (g: Grid): Grid => g[0].map((_, c) => g.map((r) => r[c]));

export function move(grid: Grid, dir: Dir): { grid: Grid; score: number; moved: boolean } {
  let g = grid.map((r) => r.slice());
  if (dir === 'up' || dir === 'down') g = transpose(g);
  if (dir === 'right' || dir === 'down') g = g.map((r) => r.reverse());
  let score = 0;
  g = g.map((r) => { const s = slideRow(r); score += s.score; return s.row; });
  if (dir === 'right' || dir === 'down') g = g.map((r) => r.reverse());
  if (dir === 'up' || dir === 'down') g = transpose(g);
  const moved = g.some((r, i) => r.some((v, j) => v !== grid[i][j]));
  return { grid: g, score, moved };
}

export function canMove(grid: Grid): boolean {
  return (['left', 'right', 'up', 'down'] as Dir[]).some((d) => move(grid, d).moved);
}
