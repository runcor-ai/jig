import { COLS, ROWS, pieceCells } from './pieces';
import type { Piece, PieceKind } from './pieces';

export type Cell = PieceKind | null;
export type Board = Cell[][];

export function createBoard(): Board {
  return Array.from({ length: ROWS }, () => Array<Cell>(COLS).fill(null));
}

export function collides(board: Board, piece: Piece): boolean {
  return pieceCells(piece).some(
    ([x, y]) => x < 0 || x >= COLS || y < 0 || y >= ROWS || board[y][x] !== null,
  );
}

export function merge(board: Board, piece: Piece): Board {
  const next = board.map((r) => r.slice());
  for (const [x, y] of pieceCells(piece)) {
    if (y >= 0 && y < ROWS && x >= 0 && x < COLS) next[y][x] = piece.kind;
  }
  return next;
}

export function clearLines(board: Board): { board: Board; cleared: number } {
  const kept = board.filter((row) => row.some((c) => c === null));
  const cleared = board.length - kept.length;
  const fresh = Array.from({ length: cleared }, () => Array<Cell>(COLS).fill(null));
  return { board: [...fresh, ...kept], cleared };
}

/** Number of rows the piece can fall before colliding. */
export function dropDistance(board: Board, piece: Piece): number {
  let d = 0;
  while (!collides(board, { ...piece, y: piece.y + d + 1 })) d++;
  return d;
}
