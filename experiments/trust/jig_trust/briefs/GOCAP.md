# Capture Go

A browser Go game for two players on one screen on a small board (9 x 9 by default, 5 x 5 to 13 x 13 selectable).

- Black and white take turns placing a stone on an empty intersection, or passing. Black moves first.
- A group is a set of same-coloured stones joined up, down, left or right. Its liberties are the empty points next
  to any of its stones. A group with no liberties is captured and removed.
- Placing a stone first removes every opponent group left with no liberties. If the new stone's own group then
  has no liberties, the move is not allowed (suicide). A move is also not allowed if it would recreate the board
  exactly as it was just before the opponent's last move (the ko rule).
- Show the board, whose turn it is, the stones each player has captured, and New game and Pass buttons.

## Required game logic: `src/logic.ts`

All rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must use them.
They must not touch the DOM.

```ts
export type Stone = 'B' | 'W' | null;
export interface Game {
  size: number;
  board: Stone[][];                       // board[row][col]
  turn: 'B' | 'W';
  captured: { B: number; W: number };     // stones captured BY each player
  previous: Stone[][] | null;             // the board as it was before the last move (for the ko rule)
}

export function newGame(size: number): Game;
export function play(game: Game, row: number, col: number): Game;
export function pass(game: Game): Game;
export function liberties(game: Game, row: number, col: number): number;
export function groupAt(game: Game, row: number, col: number): [number, number][];
```

- `newGame(size)` is an empty board with black to move, nothing captured, and `previous` = `null`.
- `play` returns a **new** game (it must not change `game`) with the stone placed, captures removed and counted,
  `previous` set to the board before this move, and the turn passed. Occupied or outside points, suicide and ko
  return the **same game object**.
- `pass` returns a new game with the turn passed and `previous` set to the current board.
- `groupAt` lists the stones of the group at `(row, col)` in row-then-column order (`[]` for an empty point).
  `liberties` is the number of distinct liberties of that group (0 for an empty point).
