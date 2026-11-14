export type Piece = 'b' | 'w' | 'B' | 'W' | null;
export interface Game { board: Piece[][]; turn: 'b' | 'w' }
export interface Move { path: [number, number][] }

const inside = (r: number, c: number) => r >= 0 && r < 8 && c >= 0 && c < 8;
const owner = (p: Piece) => (p ? p.toLowerCase() : null);
const isKing = (p: Piece) => p === 'B' || p === 'W';

export function newGame(): Game {
  const board: Piece[][] = Array.from({ length: 8 }, (_, r) => Array.from({ length: 8 }, (_, c) =>
    (r + c) % 2 === 1 ? (r <= 2 ? 'b' : r >= 5 ? 'w' : null) : null));
  return { board, turn: 'b' };
}

function dirs(p: Piece): [number, number][] {
  if (isKing(p)) return [[1, -1], [1, 1], [-1, -1], [-1, 1]];
  return owner(p) === 'b' ? [[1, -1], [1, 1]] : [[-1, -1], [-1, 1]];
}

const farRow = (side: string) => (side === 'b' ? 7 : 0);

function jumps(board: Piece[][], r: number, c: number, piece: Piece): [number, number][][] {
  const out: [number, number][][] = [];
  for (const [dr, dc] of dirs(piece)) {
    const mr = r + dr, mc = c + dc, tr = r + 2 * dr, tc = c + 2 * dc;
    if (!inside(tr, tc) || board[tr][tc] !== null) continue;
    const mid = board[mr][mc];
    if (!mid || owner(mid) === owner(piece)) continue;
    const nb = board.map((row) => row.slice());
    nb[r][c] = null; nb[mr][mc] = null; nb[tr][tc] = piece;
    const crowned = !isKing(piece) && tr === farRow(owner(piece)!);
    const more = crowned ? [] : jumps(nb, tr, tc, piece);
    if (more.length) for (const m of more) out.push([[tr, tc], ...m]);
    else out.push([[tr, tc]]);
  }
  return out;
}

export function legalMoves(g: Game): Move[] {
  const caps: Move[] = [], simple: Move[] = [];
  for (let r = 0; r < 8; r++) for (let c = 0; c < 8; c++) {
    const p = g.board[r][c];
    if (owner(p) !== g.turn) continue;
    for (const j of jumps(g.board, r, c, p)) caps.push({ path: [[r, c], ...j] });
    for (const [dr, dc] of dirs(p)) {
      const tr = r + dr, tc = c + dc;
      if (inside(tr, tc) && g.board[tr][tc] === null) simple.push({ path: [[r, c], [tr, tc]] });
    }
  }
  return caps.length ? caps : simple;
}

export function play(g: Game, move: Move): Game {
  const key = JSON.stringify(move.path);
  if (!legalMoves(g).some((m) => JSON.stringify(m.path) === key)) return g;
  const board = g.board.map((row) => row.slice());
  const [sr, sc] = move.path[0];
  let piece = board[sr][sc];
  board[sr][sc] = null;
  for (let i = 1; i < move.path.length; i++) {
    const [ar, ac] = move.path[i - 1], [br, bc] = move.path[i];
    if (Math.abs(br - ar) === 2) board[(ar + br) / 2][(ac + bc) / 2] = null;
  }
  const [er, ec] = move.path[move.path.length - 1];
  if (!isKing(piece) && er === farRow(g.turn)) piece = g.turn === 'b' ? 'B' : 'W';
  board[er][ec] = piece;
  return { board, turn: g.turn === 'b' ? 'w' : 'b' };
}
