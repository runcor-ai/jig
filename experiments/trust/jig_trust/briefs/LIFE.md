# Game of Life

A browser version of Conway's Game of Life.

- A 30 x 20 grid of cells, each alive or dead. Clicking a cell toggles it. Play / Pause runs one generation
  every 200 ms; Step advances one generation; Clear kills every cell; Random fills about a quarter of the cells.
- Each generation follows the standard rules: a live cell with two or three live neighbours stays alive; a dead
  cell with exactly three live neighbours becomes alive; every other cell is dead in the next generation. Cells
  outside the grid count as dead (the edges do not wrap). Show the generation number.

## Required game logic: `src/logic.ts`

All game rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must
use them. They must not touch the DOM.

```ts
export type Cells = boolean[][];     // cells[row][col], true = alive

export function neighbors(cells: Cells, row: number, col: number): number;
export function step(cells: Cells): Cells;
export function fromStrings(lines: string[]): Cells;
export function toStrings(cells: Cells): string[];
```

- `neighbors` counts the live cells among the up to eight around `(row, col)`; cells outside the grid are dead.
- `step` returns the next generation as a **new** grid of the same size. It must not change `cells`.
- `fromStrings` reads one string per row, `'#'` for alive and `'.'` for dead; `toStrings` does the reverse.
