export interface State {
  walls: boolean[][]; goals: boolean[][]; boxes: boolean[][];
  player: { row: number; col: number }; moves: number;
}
export type Dir = 'up' | 'down' | 'left' | 'right';

const D: Record<Dir, [number, number]> = { up: [-1, 0], down: [1, 0], left: [0, -1], right: [0, 1] };

export function parse(level: string[]): State {
  let player = { row: 0, col: 0 };
  const m = (f: (ch: string) => boolean) => level.map((l) => [...l].map(f));
  level.forEach((l, r) => [...l].forEach((ch, c) => { if (ch === '@' || ch === '+') player = { row: r, col: c }; }));
  return { walls: m((c) => c === '#'), goals: m((c) => c === '.' || c === '*' || c === '+'),
           boxes: m((c) => c === '$' || c === '*'), player, moves: 0 };
}

const free = (s: State, r: number, c: number) =>
  r >= 0 && r < s.walls.length && c >= 0 && c < s.walls[r].length && !s.walls[r][c];

export function move(s: State, dir: Dir): State {
  const [dr, dc] = D[dir];
  const r = s.player.row + dr, c = s.player.col + dc;
  if (!free(s, r, c)) return s;
  let boxes = s.boxes;
  if (s.boxes[r][c]) {
    const r2 = r + dr, c2 = c + dc;
    if (!free(s, r2, c2) || s.boxes[r2][c2]) return s;
    boxes = s.boxes.map((row) => row.slice());
    boxes[r][c] = false;
    boxes[r2][c2] = true;
  }
  return { ...s, boxes, player: { row: r, col: c }, moves: s.moves + 1 };
}

export function isSolved(s: State): boolean {
  return s.boxes.every((row, r) => row.every((b, c) => !b || s.goals[r][c]));
}

export function render(s: State): string[] {
  return s.walls.map((row, r) => row.map((w, c) => {
    if (w) return '#';
    const goal = s.goals[r][c];
    if (s.player.row === r && s.player.col === c) return goal ? '+' : '@';
    if (s.boxes[r][c]) return goal ? '*' : '$';
    return goal ? '.' : ' ';
  }).join(''));
}
