# Minesweeper

A browser minesweeper game.

- A 9 x 9 board with 10 mines placed at random when a new game starts. Left click reveals a cell; right click
  toggles a flag on an unrevealed cell.
- A revealed cell shows how many of its eight neighbours are mines. Revealing a cell with no neighbouring mines
  also reveals its neighbours, and so on outward.
- Revealing a mine loses the game and shows all mines. Revealing every cell that is not a mine wins. Show the
  status and a New game button.

## Required game logic: `src/logic.ts`

All game rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must
use them (the page chooses the random mine positions and passes them in). They must not touch the DOM.

```ts
export interface Board {
  width: number;
  height: number;
  mines: boolean[][];      // mines[y][x]
  revealed: boolean[][];   // revealed[y][x]
  flagged: boolean[][];    // flagged[y][x]
}

export function createBoard(width: number, height: number, mines: [number, number][]): Board; // mines as [x, y]
export function adjacent(board: Board, x: number, y: number): number;
export function reveal(board: Board, x: number, y: number): Board;
export function toggleFlag(board: Board, x: number, y: number): Board;
export function status(board: Board): 'playing' | 'won' | 'lost';
```

- `createBoard` returns a board with mines at the given `[x, y]` positions, nothing revealed and nothing flagged.
- `adjacent` counts the mines among the up to eight cells around `(x, y)`.
- `reveal` returns a **new** board (it must not change the old one) with `(x, y)` revealed. If that cell has no
  neighbouring mines, its neighbours are revealed too, repeating outward through every connected cell with no
  neighbouring mines. Flagged cells are never revealed. If the cell is outside the board, already revealed,
  flagged, or the game is over, it returns the **same board object**.
- `toggleFlag` returns a new board with the flag on `(x, y)` switched; on a revealed cell, outside the board, or
  when the game is over, it returns the same board object.
- `status` is `'lost'` once any mine is revealed, `'won'` when every non-mine cell is revealed, otherwise
  `'playing'`.
