export type Board = string[][];

export const parse = (rows: string[]): Board => rows.map((r) => [...r]);

const inside = (r: number, c: number) => r >= 0 && r < 8 && c >= 0 && c < 8;
const colorOf = (p: string) => (p === '.' ? null : p === p.toUpperCase() ? 'w' : 'b');
const name = (r: number, c: number) => 'abcdefgh'[c] + (8 - r);
const at = (sq: string): [number, number] => [8 - Number(sq[1]), 'abcdefgh'.indexOf(sq[0])];

const KN = [[1, 2], [2, 1], [-1, 2], [-2, 1], [1, -2], [2, -1], [-1, -2], [-2, -1]];
const DIAG = [[1, 1], [1, -1], [-1, 1], [-1, -1]];
const ORTH = [[1, 0], [-1, 0], [0, 1], [0, -1]];

// Squares this piece attacks or may move to, without the "own king safe" rule. Kings are never captured.
function pseudo(b: Board, r: number, c: number): [number, number][] {
  const p = b[r][c], me = colorOf(p);
  if (!me) return [];
  const out: [number, number][] = [];
  const add = (i: number, j: number) => {
    if (!inside(i, j)) return false;
    const q = b[i][j];
    if (q === '.') { out.push([i, j]); return true; }
    if (colorOf(q) !== me && q.toLowerCase() !== 'k') out.push([i, j]);
    return false;
  };
  const slide = (ds: number[][]) => { for (const [dr, dc] of ds) { let i = r + dr, j = c + dc; while (add(i, j)) { i += dr; j += dc; } } };
  switch (p.toLowerCase()) {
    case 'n': KN.forEach(([dr, dc]) => add(r + dr, c + dc)); break;
    case 'b': slide(DIAG); break;
    case 'r': slide(ORTH); break;
    case 'q': slide([...DIAG, ...ORTH]); break;
    case 'k': [...DIAG, ...ORTH].forEach(([dr, dc]) => add(r + dr, c + dc)); break;
    case 'p': {
      const d = me === 'w' ? -1 : 1, start = me === 'w' ? 6 : 1;
      if (inside(r + d, c) && b[r + d][c] === '.') {
        out.push([r + d, c]);
        if (r === start && b[r + 2 * d][c] === '.') out.push([r + 2 * d, c]);
      }
      for (const dc of [-1, 1]) {
        const i = r + d, j = c + dc;
        if (inside(i, j) && b[i][j] !== '.' && colorOf(b[i][j]) !== me && b[i][j].toLowerCase() !== 'k') out.push([i, j]);
      }
    }
  }
  return out;
}

function attacked(b: Board, r: number, c: number, by: 'w' | 'b'): boolean {
  for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) {
    const p = b[i][j];
    if (colorOf(p) !== by) continue;
    const t = p.toLowerCase();
    if (t === 'p') {
      const d = by === 'w' ? -1 : 1;
      if (i + d === r && Math.abs(j - c) === 1) return true;
    } else if (t === 'k') {
      if (Math.max(Math.abs(i - r), Math.abs(j - c)) === 1) return true;
    } else {
      // sliding and knight attacks: treat the target square as capturable
      const saved = b[r][c];
      b[r][c] = by === 'w' ? 'x' : 'X';
      const hit = pseudo(b, i, j).some(([a, e]) => a === r && e === c);
      b[r][c] = saved;
      if (hit) return true;
    }
  }
  return false;
}

export function inCheck(b: Board, color: 'w' | 'b'): boolean {
  const k = color === 'w' ? 'K' : 'k';
  for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) if (b[i][j] === k) return attacked(b, i, j, color === 'w' ? 'b' : 'w');
  return false;
}

function legal(b: Board, r: number, c: number): [number, number][] {
  const me = colorOf(b[r][c]) as 'w' | 'b';
  return pseudo(b, r, c).filter(([i, j]) => {
    const nb = b.map((row) => row.slice());
    nb[i][j] = nb[r][c];
    nb[r][c] = '.';
    return !inCheck(nb, me);
  });
}

export function moves(b: Board, square: string): string[] {
  const [r, c] = at(square);
  if (!inside(r, c) || b[r][c] === '.') return [];
  return legal(b, r, c).map(([i, j]) => name(i, j)).sort();
}

export function isCheckmate(b: Board, color: 'w' | 'b'): boolean {
  if (!inCheck(b, color)) return false;
  for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) if (colorOf(b[i][j]) === color && legal(b, i, j).length) return false;
  return true;
}
