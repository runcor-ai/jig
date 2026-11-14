# Lights out

A browser lights-out puzzle on a 5 x 5 grid of lights.

- Clicking a light toggles it and its up, down, left and right neighbours (on becomes off, off becomes on).
  Lights on the edge have fewer neighbours; nothing wraps around.
- The goal is to switch every light off. A new puzzle starts from all lights off and applies 10 random presses,
  so every puzzle can be solved. Show the number of presses made, a message when solved, and a New puzzle button.

## Required game logic: `src/logic.ts`

All game rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must
use them (the page chooses the random presses). They must not touch the DOM.

```ts
export type Board = boolean[][];   // board[row][col], true = light on

export function create(n: number, on: [number, number][]): Board;   // on: [row, col] pairs
export function press(board: Board, row: number, col: number): Board;
export function isSolved(board: Board): boolean;
export function countOn(board: Board): number;
```

- `create(n, on)` returns an n x n board with the lights at the given `[row, col]` positions on and all others off.
- `press` returns a **new** board (it must not change `board`) with the light at `(row, col)` and its existing
  up, down, left and right neighbours toggled. Pressing outside the board returns the **same board object**.
- `isSolved` is `true` when every light is off. `countOn` is the number of lights that are on.
