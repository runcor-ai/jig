export type PieceKind = 'I' | 'O' | 'T' | 'S' | 'Z' | 'J' | 'L';
export type Matrix = number[][];

export const COLS = 10;
export const ROWS = 20;

export const KINDS: PieceKind[] = ['I', 'O', 'T', 'S', 'Z', 'J', 'L'];

/** Base (rotation 0) matrices. 1 = filled. */
const BASE: Record<PieceKind, Matrix> = {
  I: [
    [0, 0, 0, 0],
    [1, 1, 1, 1],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
  ],
  O: [
    [1, 1],
    [1, 1],
  ],
  T: [
    [0, 1, 0],
    [1, 1, 1],
    [0, 0, 0],
  ],
  S: [
    [0, 1, 1],
    [1, 1, 0],
    [0, 0, 0],
  ],
  Z: [
    [1, 1, 0],
    [0, 1, 1],
    [0, 0, 0],
  ],
  J: [
    [1, 0, 0],
    [1, 1, 1],
    [0, 0, 0],
  ],
  L: [
    [0, 0, 1],
    [1, 1, 1],
    [0, 0, 0],
  ],
};

/** Rotate a square matrix 90 degrees clockwise. */
export function rotateMatrix(m: Matrix): Matrix {
  const n = m.length;
  return m.map((_, r) => m.map((__, c) => m[n - 1 - c][r]));
}

/** Rotation states per kind, defined as data (computed once from the base matrices). */
export const ROTATIONS: Record<PieceKind, Matrix[]> = Object.fromEntries(
  KINDS.map((k) => {
    const states: Matrix[] = [BASE[k]];
    for (let i = 1; i < 4; i++) states.push(rotateMatrix(states[i - 1]));
    return [k, states];
  }),
) as Record<PieceKind, Matrix[]>;

export interface Piece {
  kind: PieceKind;
  rotation: number; // 0..3
  x: number; // column of matrix left edge
  y: number; // row of matrix top edge
}

export function matrixOf(kind: PieceKind, rotation: number): Matrix {
  return ROTATIONS[kind][((rotation % 4) + 4) % 4];
}

/** Absolute board cells [x, y] occupied by a piece. */
export function pieceCells(p: Piece): [number, number][] {
  const out: [number, number][] = [];
  matrixOf(p.kind, p.rotation).forEach((row, r) =>
    row.forEach((v, c) => {
      if (v) out.push([p.x + c, p.y + r]);
    }),
  );
  return out;
}

/** New piece at rotation 0, horizontally centred at the top. */
export function spawnPiece(kind: PieceKind): Piece {
  const size = ROTATIONS[kind][0].length;
  return { kind, rotation: 0, x: Math.floor((COLS - size) / 2), y: 0 };
}

export function rotatePiece(p: Piece): Piece {
  return { ...p, rotation: (p.rotation + 1) % 4 };
}

export function randomPiece(rng: () => number): PieceKind {
  const i = Math.min(KINDS.length - 1, Math.max(0, Math.floor(rng() * KINDS.length)));
  return KINDS[i];
}
