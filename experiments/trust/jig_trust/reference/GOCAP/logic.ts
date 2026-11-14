export type Stone = 'B' | 'W' | null;
export interface Game {
  size: number; board: Stone[][]; turn: 'B' | 'W';
  captured: { B: number; W: number }; previous: Stone[][] | null;
}

export const newGame = (size: number): Game => ({
  size, board: Array.from({ length: size }, () => Array(size).fill(null)), turn: 'B', captured: { B: 0, W: 0 },
  previous: null,
});

const nbrs = (n: number, r: number, c: number): [number, number][] =>
  ([[r - 1, c], [r + 1, c], [r, c - 1], [r, c + 1]] as [number, number][]).filter(([i, j]) => i >= 0 && j >= 0 && i < n && j < n);

function group(board: Stone[][], r: number, c: number): [number, number][] {
  const color = board[r][c];
  if (!color) return [];
  const seen = new Set([`${r},${c}`]), stack: [number, number][] = [[r, c]], out: [number, number][] = [];
  while (stack.length) {
    const [i, j] = stack.pop()!;
    out.push([i, j]);
    for (const [a, b] of nbrs(board.length, i, j))
      if (board[a][b] === color && !seen.has(`${a},${b}`)) { seen.add(`${a},${b}`); stack.push([a, b]); }
  }
  return out.sort((x, y) => x[0] - y[0] || x[1] - y[1]);
}

function libs(board: Stone[][], r: number, c: number): number {
  const s = new Set<string>();
  for (const [i, j] of group(board, r, c))
    for (const [a, b] of nbrs(board.length, i, j)) if (board[a][b] === null) s.add(`${a},${b}`);
  return s.size;
}

export const groupAt = (g: Game, r: number, c: number) => group(g.board, r, c);
export const liberties = (g: Game, r: number, c: number) => libs(g.board, r, c);
const same = (a: Stone[][] | null, b: Stone[][]) => !!a && a.every((row, i) => row.every((v, j) => v === b[i][j]));

export function play(g: Game, r: number, c: number): Game {
  const n = g.size;
  if (r < 0 || c < 0 || r >= n || c >= n || g.board[r][c] !== null) return g;
  const me = g.turn, opp = me === 'B' ? 'W' : 'B';
  const board = g.board.map((row) => row.slice());
  board[r][c] = me;
  let taken = 0;
  for (const [a, b] of nbrs(n, r, c))
    if (board[a][b] === opp && libs(board, a, b) === 0)
      for (const [i, j] of group(board, a, b)) { board[i][j] = null; taken++; }
  if (libs(board, r, c) === 0) return g;
  if (same(g.previous, board)) return g;
  return { size: n, board, turn: opp, captured: { ...g.captured, [me]: g.captured[me] + taken }, previous: g.board };
}

export const pass = (g: Game): Game => ({ ...g, turn: g.turn === 'B' ? 'W' : 'B', previous: g.board });
