# Four in a row

A browser four-in-a-row game for two players on one screen, with red and yellow discs.

- A grid of 7 columns and 6 rows standing upright. Red moves first, then the players alternate.
- Clicking a column drops the current player's disc into it; the disc falls to the lowest empty row.
- The first player with four of their discs in a line (across, up and down, or diagonally) wins. If the grid
  fills up with no winner, it is a draw. Show whose turn it is, the result, and a New game button.

## Required game logic: `src/logic.ts`

All game rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must
use them. They must not touch the DOM.

```ts
export type Disc = 'R' | 'Y';
export interface Game {
  cols: number;
  rows: number;
  grid: (Disc | null)[][];   // grid[row][col]; row 0 is the TOP row
  turn: Disc;
}

export function newGame(cols?: number, rows?: number): Game;   // defaults 7 and 6
export function drop(game: Game, col: number): Game;
export function winner(game: Game): Disc | 'draw' | null;
```

- `newGame(cols = 7, rows = 6)` returns an empty grid with `turn` = `'R'`.
- `drop(game, col)` returns a **new** game (it must not change `game`) with the current player's disc in the
  lowest empty row of column `col`, and the turn passed to the other player. If the column is full, out of
  range, or the game is already over, it returns the **same `game` object**.
- `winner(game)` returns the disc with four in a line horizontally, vertically or diagonally, `'draw'` when the
  grid is full with no winner, and `null` otherwise.
