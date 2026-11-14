# Number grid puzzle

A browser 9 x 9 number puzzle (sudoku) with at least three built-in puzzles.

- Some cells are given and cannot be changed. The player selects an empty cell and types a digit 1 to 9, or
  clears it.
- A digit that repeats in its row, column or 3 x 3 box is highlighted as a conflict. A Hint button shows which
  digits are still possible in the selected cell.
- The puzzle is solved when every cell is filled with no conflicts. Show a message when solved, and Next puzzle
  and Reset buttons.

## Required game logic: `src/logic.ts`

All game rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must
use them. They must not touch the DOM.

```ts
export type Grid = number[][];   // 9 rows of 9; 0 means empty

export function parse(s: string): Grid;   // 81 characters, row by row: '1'-'9', or '0' or '.' for empty
export function conflicts(grid: Grid): [number, number][];
export function candidates(grid: Grid, row: number, col: number): number[];
export function place(grid: Grid, row: number, col: number, digit: number): Grid;
export function isSolved(grid: Grid): boolean;
```

- `parse` reads an 81-character string row by row.
- `conflicts` lists every filled cell `[row, col]` whose digit also appears elsewhere in its row, column or 3 x 3
  box, in row-then-column order, each cell once.
- `candidates` lists, in ascending order, the digits 1 to 9 that do not already appear in the cell's row, column
  or box. A filled cell has no candidates (`[]`).
- `place` returns a **new** grid with `digit` (0 to 9, where 0 clears) at `(row, col)`. It must not change
  `grid`. Out-of-range positions or digits return the **same grid object**.
- `isSolved` is `true` when every cell is filled and there are no conflicts.
