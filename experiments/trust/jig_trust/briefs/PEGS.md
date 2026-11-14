# Peg jump

A browser peg-jumping puzzle on a 7 x 7 cross-shaped board of 33 holes.

- At the start every hole has a peg except the centre. A move jumps a peg over a neighbouring peg (up, down, left
  or right) into an empty hole directly beyond; the jumped peg is removed.
- The player clicks a peg, then the hole to jump into. The game ends when no jump is possible. Show the pegs left,
  a message when only one peg remains (with "perfect" if it is in the centre), an Undo button and a Restart
  button.

## Required game logic: `src/logic.ts`

All game rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must
use them. They must not touch the DOM.

```ts
export type Cell = 'peg' | 'empty' | 'off';     // 'off' = not part of the board
export type Board = Cell[][];                    // board[row][col]

export function standard(): Board;               // the 7 x 7 cross with the centre empty
export function fromStrings(lines: string[]): Board;   // 'o' peg, '.' empty, ' ' off
export function canJump(board: Board, row: number, col: number, toRow: number, toCol: number): boolean;
export function jump(board: Board, row: number, col: number, toRow: number, toCol: number): Board;
export function pegsLeft(board: Board): number;
export function hasMoves(board: Board): boolean;
```

- `standard()` is the cross: rows 0, 1, 5 and 6 have holes only in columns 2 to 4; rows 2 to 4 have all seven.
  Every hole has a peg except the centre `(3, 3)`.
- `canJump` is `true` when `(row, col)` has a peg, `(toRow, toCol)` is an empty hole exactly two cells away in a
  straight line (up, down, left or right), and the cell between them has a peg.
- `jump` returns a **new** board with the jump made (it must not change `board`). If the jump is not allowed, it
  returns the **same board object**.
- `pegsLeft` counts the pegs. `hasMoves` is `true` when any jump is possible.
