export type Disc = 'R' | 'Y';
export interface Game { cols: number; rows: number; grid: (Disc | null)[][]; turn: Disc }

export function newGame(cols = 7, rows = 6): Game {
  return { cols, rows, grid: Array.from({ length: rows }, () => Array(cols).fill(null)), turn: 'R' };
}

export function winner(g: Game): Disc | 'draw' | null {
  const at = (r: number, c: number) => (r >= 0 && c >= 0 && r < g.rows && c < g.cols ? g.grid[r][c] : null);
  for (let r = 0; r < g.rows; r++) for (let c = 0; c < g.cols; c++) {
    const d = g.grid[r][c];
    if (!d) continue;
    for (const [dr, dc] of [[0, 1], [1, 0], [1, 1], [1, -1]])
      if ([1, 2, 3].every((k) => at(r + dr * k, c + dc * k) === d)) return d;
  }
  return g.grid.every((row) => row.every((x) => x !== null)) ? 'draw' : null;
}

export function drop(g: Game, col: number): Game {
  if (!Number.isInteger(col) || col < 0 || col >= g.cols || winner(g) !== null) return g;
  for (let r = g.rows - 1; r >= 0; r--) {
    if (g.grid[r][col] === null) {
      const grid = g.grid.map((row) => row.slice());
      grid[r][col] = g.turn;
      return { ...g, grid, turn: g.turn === 'R' ? 'Y' : 'R' };
    }
  }
  return g;
}
