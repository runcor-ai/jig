export type Board = number[];

export const solved = (): Board => [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 0];

function neighbours(i: number): number[] {
  const r = Math.floor(i / 4), c = i % 4, out: number[] = [];
  if (r > 0) out.push(i - 4);
  if (r < 3) out.push(i + 4);
  if (c > 0) out.push(i - 1);
  if (c < 3) out.push(i + 1);
  return out;
}

export function movable(b: Board): number[] {
  return neighbours(b.indexOf(0)).map((i) => b[i]).sort((x, y) => x - y);
}

export function slide(b: Board, tile: number): Board {
  const gap = b.indexOf(0), at = b.indexOf(tile);
  if (tile === 0 || at === -1 || !neighbours(gap).includes(at)) return b;
  const next = b.slice();
  next[gap] = tile;
  next[at] = 0;
  return next;
}

export const isSolved = (b: Board) => b.every((v, i) => v === solved()[i]);
