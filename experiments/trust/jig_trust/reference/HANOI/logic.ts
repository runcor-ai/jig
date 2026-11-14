export interface Game { pegs: number[][]; moves: number }

export const newGame = (n: number): Game => ({ pegs: [Array.from({ length: n }, (_, i) => n - i), [], []], moves: 0 });

const top = (p: number[]) => (p.length ? p[p.length - 1] : Infinity);

export function canMove(g: Game, from: number, to: number): boolean {
  const ok = (x: number) => Number.isInteger(x) && x >= 0 && x <= 2;
  return ok(from) && ok(to) && from !== to && g.pegs[from].length > 0 && top(g.pegs[from]) < top(g.pegs[to]);
}

export function move(g: Game, from: number, to: number): Game {
  if (!canMove(g, from, to)) return g;
  const pegs = g.pegs.map((p) => p.slice());
  pegs[to].push(pegs[from].pop()!);
  return { pegs, moves: g.moves + 1 };
}

export const isSolved = (g: Game) => g.pegs[0].length === 0 && g.pegs[1].length === 0 && g.pegs[2].length > 0;
export const fewestMoves = (n: number) => 2 ** n - 1;
