export type Mark = 'X' | 'O';
export type Cell = Mark | null;
export interface Game { board: Cell[]; turn: Mark }

const LINES = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]];

export function newGame(): Game {
  return { board: Array(9).fill(null), turn: 'X' };
}

export function winner(game: Game): Mark | 'draw' | null {
  for (const [a, b, c] of LINES) {
    const m = game.board[a];
    if (m && m === game.board[b] && m === game.board[c]) return m;
  }
  return game.board.every((c) => c !== null) ? 'draw' : null;
}

export function play(game: Game, cell: number): Game {
  if (!Number.isInteger(cell) || cell < 0 || cell > 8 || game.board[cell] !== null || winner(game) !== null) return game;
  const board = game.board.slice();
  board[cell] = game.turn;
  return { board, turn: game.turn === 'X' ? 'O' : 'X' };
}
