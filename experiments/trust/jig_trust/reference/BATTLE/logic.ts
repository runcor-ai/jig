export interface Ship { name: string; row: number; col: number; length: number; horizontal: boolean }
export interface Game { size: number; ships: Ship[]; shots: [number, number][] }

export function cells(s: Ship): [number, number][] {
  return Array.from({ length: s.length }, (_, k) => (s.horizontal ? [s.row, s.col + k] : [s.row + k, s.col]) as [number, number]);
}

const key = ([r, c]: [number, number]) => `${r},${c}`;

export function canPlace(size: number, ships: Ship[], ship: Ship): boolean {
  const taken = new Set(ships.flatMap(cells).map(key));
  return cells(ship).every(([r, c]) => r >= 0 && c >= 0 && r < size && c < size && !taken.has(key([r, c])));
}

export const newGame = (size: number, ships: Ship[]): Game => ({ size, ships: ships.slice(), shots: [] });

const shot = (g: Game, r: number, c: number) => g.shots.some(([a, b]) => a === r && b === c);

export const isWon = (g: Game) => g.ships.every((s) => cells(s).every(([r, c]) => shot(g, r, c)));

export function fire(g: Game, row: number, col: number): Game {
  if (row < 0 || col < 0 || row >= g.size || col >= g.size || shot(g, row, col) || isWon(g)) return g;
  return { ...g, shots: [...g.shots, [row, col]] };
}

export function result(g: Game, row: number, col: number): 'miss' | 'hit' | 'sunk' | 'unknown' {
  if (!shot(g, row, col)) return 'unknown';
  const ship = g.ships.find((s) => cells(s).some(([r, c]) => r === row && c === col));
  if (!ship) return 'miss';
  return cells(ship).every(([r, c]) => shot(g, r, c)) ? 'sunk' : 'hit';
}
