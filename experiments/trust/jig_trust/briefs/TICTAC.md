# Tic-tac-toe

A browser tic-tac-toe game for two players taking turns on one screen.

- A 3 x 3 board. X always moves first, then the players alternate.
- Clicking an empty cell places the current player's mark there.
- The game ends when a player has three in a row (a row, a column or a diagonal), or when the board is full
  with no winner (a draw). Show whose turn it is, the result when the game ends, and a New game button.

## Required game logic: `src/logic.ts`

All game rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must
use them. They must not touch the DOM.

```ts
export type Mark = 'X' | 'O';
export type Cell = Mark | null;
export interface Game { board: Cell[]; turn: Mark }   // board: 9 cells, row by row (index 0 = top left)

export function newGame(): Game;
export function play(game: Game, cell: number): Game;
export function winner(game: Game): Mark | 'draw' | null;
```

- `newGame()` returns a game with 9 empty cells (`null`) and `turn` = `'X'`.
- `play(game, cell)` returns a **new** game with the current player's mark at `cell` (0 to 8) and the turn
  passed to the other player. It must not change `game`. If the cell is taken, out of range, or the game is
  already over, it returns the **same `game` object** unchanged.
- `winner(game)` returns `'X'` or `'O'` if that player has three in a row, `'draw'` if the board is full with no
  three in a row, and `null` while the game is still going.
