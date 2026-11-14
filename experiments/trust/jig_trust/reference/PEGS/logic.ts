export type Cell = 'peg' | 'empty' | 'off';
export type Board = Cell[][];

export function standard(): Board {
  return Array.from({ length: 7 }, (_, r) => Array.from({ length: 7 }, (_, c) => {
    const on = (r >= 2 && r <= 4) || (c >= 2 && c <= 4);
    if (!on) return 'off';
    return r === 3 && c === 3 ? 'empty' : 'peg';
  }));
}

export const fromStrings = (lines: string[]): Board =>
  lines.map((l) => [...l].map((ch) => (ch === 'o' ? 'peg' : ch === '.' ? 'empty' : 'off')));

const at = (b: Board, r: number, c: number): Cell => (r >= 0 && r < b.length && c >= 0 && c < b[r].length ? b[r][c] : 'off');

export function canJump(b: Board, r: number, c: number, tr: number, tc: number): boolean {
  const dr = tr - r, dc = tc - c;
  const straight = (Math.abs(dr) === 2 && dc === 0) || (Math.abs(dc) === 2 && dr === 0);
  return straight && at(b, r, c) === 'peg' && at(b, tr, tc) === 'empty' && at(b, r + dr / 2, c + dc / 2) === 'peg';
}

export function jump(b: Board, r: number, c: number, tr: number, tc: number): Board {
  if (!canJump(b, r, c, tr, tc)) return b;
  const n = b.map((row) => row.slice());
  n[r][c] = 'empty';
  n[(r + tr) / 2][(c + tc) / 2] = 'empty';
  n[tr][tc] = 'peg';
  return n;
}

export const pegsLeft = (b: Board) => b.flat().filter((x) => x === 'peg').length;

export function hasMoves(b: Board): boolean {
  for (let r = 0; r < b.length; r++) for (let c = 0; c < b[r].length; c++)
    for (const [dr, dc] of [[2, 0], [-2, 0], [0, 2], [0, -2]]) if (canJump(b, r, c, r + dr, c + dc)) return true;
  return false;
}
