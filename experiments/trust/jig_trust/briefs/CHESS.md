# Chess moves

A browser chess board for two players on one screen. Clicking a piece of the side to move highlights its legal
destination squares; clicking one of them makes the move. Show whose turn it is, "check" when a king is attacked,
and "checkmate" when the side to move is in check with no legal move. Include a Reset button. Castling, en passant
and promotion choices are not needed (a pawn reaching the last rank may simply stay a pawn).

## Required game logic: `src/logic.ts`

All rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must use them.
They must not touch the DOM.

A board is 8 strings, one per rank, **rank 8 first**; each string has 8 characters for files a to h: `K Q R B N P`
for white pieces, `k q r b n p` for black, `.` for empty. Squares are named like `'e4'`.

```ts
export type Board = string[][];   // board[row][col]; row 0 is rank 8, col 0 is file a

export function parse(rows: string[]): Board;
export function moves(board: Board, square: string): string[];
export function inCheck(board: Board, color: 'w' | 'b'): boolean;
export function isCheckmate(board: Board, color: 'w' | 'b'): boolean;
```

- `parse` turns the 8 strings into a board.
- `moves(board, square)` lists the legal destination squares of the piece on `square`, sorted alphabetically
  (`[]` for an empty square). Pieces move by the normal rules: knights jump; bishops, rooks and queens slide until
  blocked, and may capture the first enemy piece in the way; kings move one square. A white pawn moves one square
  towards rank 8 to an empty square, two from rank 2 if both squares are empty, and captures one square diagonally
  forward; black pawns the same towards rank 1 (two from rank 7). A move is legal only if it does not leave the
  mover's own king attacked, so pinned pieces and kings walking into attack are limited. Nobody can capture a king.
- `inCheck(board, color)` is `true` when that colour's king is attacked.
- `isCheckmate(board, color)` is `true` when that colour is in check and none of its pieces has a legal move.
