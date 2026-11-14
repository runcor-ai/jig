export type Disc = 'B' | 'W';
export interface Game { board: (Disc | null)[][]; turn: Disc }

const DIRS = [[-1, -1], [-1, 0], [-1, 1], [0, -1], [0, 1], [1, -1], [1, 0], [1, 1]];
const other = (d: Disc): Disc => (d === 'B' ? 'W' : 'B');
const inside = (r: number, c: number) => r >= 0 && r < 8 && c >= 0 && c < 8;

export function newGame(): Game {
  const board: (Disc | null)[][] = Array.from({ length: 8 }, () => Array(8).fill(null));
  board[3][3] = 'W'; board[4][4] = 'W'; board[3][4] = 'B'; board[4][3] = 'B';
  return { board, turn: 'B' };
}

function flips(board: (Disc | null)[][], me: Disc, r: number, c: number): [number, number][] {
  if (!inside(r, c) || board[r][c] !== null) return [];
  const out: [number, number][] = [];
  for (const [dr, dc] of DIRS) {
    const line: [number, number][] = [];
    let i = r + dr, j = c + dc;
    while (inside(i, j) && board[i][j] === other(me)) { line.push([i, j]); i += dr; j += dc; }
    if (line.length && inside(i, j) && board[i][j] === me) out.push(...line);
  }
  return out;
}

function movesFor(board: (Disc | null)[][], me: Disc): [number, number][] {
  const out: [number, number][] = [];
  for (let r = 0; r < 8; r++) for (let c = 0; c < 8; c++) if (flips(board, me, r, c).length) out.push([r, c]);
  return out;
}

export const legalMoves = (g: Game) => movesFor(g.board, g.turn);

export function play(g: Game, row: number, col: number): Game {
  const f = flips(g.board, g.turn, row, col);
  if (!f.length) return g;
  const board = g.board.map((r) => r.slice());
  board[row][col] = g.turn;
  for (const [i, j] of f) board[i][j] = g.turn;
  const next = movesFor(board, other(g.turn)).length ? other(g.turn) : g.turn;
  return { board, turn: next };
}

export function score(g: Game): { B: number; W: number } {
  const flat = g.board.flat();
  return { B: flat.filter((x) => x === 'B').length, W: flat.filter((x) => x === 'W').length };
}

export const isOver = (g: Game) => !movesFor(g.board, 'B').length && !movesFor(g.board, 'W').length;
