import type { PieceKind, Point } from './pieces';

export const BOARD_WIDTH = 10;
export const BOARD_HEIGHT = 20;
export type Cell = PieceKind | null;
export type Board = Cell[][];

export function createBoard(): Board {
  return Array.from({ length: BOARD_HEIGHT }, () => Array<Cell>(BOARD_WIDTH).fill(null));
}

/** True if any cell is outside the walls/floor or overlaps a locked cell. */
export function collides(board: Board, cells: Point[]): boolean {
  return cells.some(
    ({ x, y }) => x < 0 || x >= BOARD_WIDTH || y >= BOARD_HEIGHT || (y >= 0 && board[y][x] !== null),
  );
}

export function mergePiece(board: Board, cells: Point[], kind: PieceKind): Board {
  const next = board.map((r) => r.slice());
  for (const { x, y } of cells) if (y >= 0 && y < BOARD_HEIGHT) next[y][x] = kind;
  return next;
}

export function clearFullRows(board: Board): { board: Board; cleared: number } {
  const kept = board.filter((row) => row.some((c) => c === null));
  const cleared = board.length - kept.length;
  const fresh = Array.from({ length: cleared }, () => Array<Cell>(BOARD_WIDTH).fill(null));
  return { board: [...fresh, ...kept], cleared };
}
