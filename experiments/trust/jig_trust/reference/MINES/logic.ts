export interface Board {
  width: number; height: number;
  mines: boolean[][]; revealed: boolean[][]; flagged: boolean[][];
}

const grid = (w: number, h: number) => Array.from({ length: h }, () => Array(w).fill(false));
const inside = (b: Board, x: number, y: number) => x >= 0 && y >= 0 && x < b.width && y < b.height;

export function createBoard(width: number, height: number, mines: [number, number][]): Board {
  const m = grid(width, height);
  for (const [x, y] of mines) m[y][x] = true;
  return { width, height, mines: m, revealed: grid(width, height), flagged: grid(width, height) };
}

export function adjacent(b: Board, x: number, y: number): number {
  let n = 0;
  for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++)
    if ((dx || dy) && inside(b, x + dx, y + dy) && b.mines[y + dy][x + dx]) n++;
  return n;
}

export function status(b: Board): 'playing' | 'won' | 'lost' {
  let hidden = 0;
  for (let y = 0; y < b.height; y++) for (let x = 0; x < b.width; x++) {
    if (b.mines[y][x] && b.revealed[y][x]) return 'lost';
    if (!b.mines[y][x] && !b.revealed[y][x]) hidden++;
  }
  return hidden === 0 ? 'won' : 'playing';
}

export function reveal(b: Board, x: number, y: number): Board {
  if (!inside(b, x, y) || b.revealed[y][x] || b.flagged[y][x] || status(b) !== 'playing') return b;
  const revealed = b.revealed.map((r) => r.slice());
  const stack: [number, number][] = [[x, y]];
  while (stack.length) {
    const [cx, cy] = stack.pop()!;
    if (!inside(b, cx, cy) || revealed[cy][cx] || b.flagged[cy][cx]) continue;
    revealed[cy][cx] = true;
    if (!b.mines[cy][cx] && adjacent(b, cx, cy) === 0)
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (dx || dy) stack.push([cx + dx, cy + dy]);
  }
  return { ...b, revealed };
}

export function toggleFlag(b: Board, x: number, y: number): Board {
  if (!inside(b, x, y) || b.revealed[y][x] || status(b) !== 'playing') return b;
  const flagged = b.flagged.map((r) => r.slice());
  flagged[y][x] = !flagged[y][x];
  return { ...b, flagged };
}
