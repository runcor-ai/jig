export type PieceKind = 'bar' | 'block' | 'tee' | 'hookL' | 'hookR' | 'stepS' | 'stepZ';
export interface Point { x: number; y: number }

export interface PieceDef {
  name: string;
  color: string;
  size: number;
  /** Four rotation states (clockwise), each exactly four cells. */
  rotations: Point[][];
}

const p = (x: number, y: number): Point => ({ x, y });

interface Base { name: string; color: string; size: number; cells: Point[] }

const BASES: Record<PieceKind, Base> = {
  bar: { name: 'Bar', color: '#2ec4b6', size: 4, cells: [p(0, 1), p(1, 1), p(2, 1), p(3, 1)] },
  block: { name: 'Block', color: '#ffbf47', size: 2, cells: [p(0, 0), p(1, 0), p(0, 1), p(1, 1)] },
  tee: { name: 'Tee', color: '#9b6bdc', size: 3, cells: [p(1, 0), p(0, 1), p(1, 1), p(2, 1)] },
  hookL: { name: 'Hook-L', color: '#ff8c42', size: 3, cells: [p(0, 0), p(0, 1), p(1, 1), p(2, 1)] },
  hookR: { name: 'Hook-R', color: '#4f8cff', size: 3, cells: [p(2, 0), p(0, 1), p(1, 1), p(2, 1)] },
  stepS: { name: 'Step-S', color: '#7bd85a', size: 3, cells: [p(1, 0), p(2, 0), p(0, 1), p(1, 1)] },
  stepZ: { name: 'Step-Z', color: '#ff5d73', size: 3, cells: [p(0, 0), p(1, 0), p(1, 1), p(2, 1)] },
};

function rotateCw(cells: Point[], size: number): Point[] {
  return cells.map((c) => p(size - 1 - c.y, c.x));
}

function build(base: Base): PieceDef {
  const rotations: Point[][] = [base.cells];
  for (let i = 1; i < 4; i++) rotations.push(rotateCw(rotations[i - 1], base.size));
  return { name: base.name, color: base.color, size: base.size, rotations };
}

export const PIECE_KINDS: PieceKind[] = ['bar', 'block', 'tee', 'hookL', 'hookR', 'stepS', 'stepZ'];

export const PIECES: Record<PieceKind, PieceDef> = Object.fromEntries(
  PIECE_KINDS.map((k) => [k, build(BASES[k])]),
) as Record<PieceKind, PieceDef>;

export function cellsFor(kind: PieceKind, rotation: number): Point[] {
  return PIECES[kind].rotations[((rotation % 4) + 4) % 4];
}
