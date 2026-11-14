# Sliding puzzle

A browser 15-puzzle: fifteen numbered tiles and one gap on a 4 x 4 board.

- Clicking a tile next to the gap slides it into the gap. The arrow keys slide the tile on the opposite side of
  the gap into it.
- A new game shuffles the board by making 200 random legal slides from the solved board, so every puzzle can be
  solved. Show the number of moves, a message when the tiles are back in order, and a New game button.

## Required game logic: `src/logic.ts`

All game rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must
use them (the page does the random shuffling). They must not touch the DOM.

```ts
export type Board = number[];   // 16 entries, row by row; 0 is the gap

export function solved(): Board;                       // [1, 2, ..., 15, 0]
export function movable(board: Board): number[];       // tiles that can slide now, in ascending order
export function slide(board: Board, tile: number): Board;
export function isSolved(board: Board): boolean;
```

- `solved()` returns the tiles 1 to 15 in order with the gap last.
- `movable(board)` lists the tiles directly above, below, left or right of the gap (not wrapping around rows),
  in ascending order.
- `slide(board, tile)` returns a **new** board with `tile` and the gap swapped (it must not change `board`). If
  `tile` is not next to the gap, it returns the **same board object**.
- `isSolved(board)` is `true` when the board equals `solved()`.
