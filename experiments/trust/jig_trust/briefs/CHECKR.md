# Checkers

A browser checkers (English draughts) game for two players on one screen, black against white, on an 8 x 8 board.

- Pieces stand only on the dark squares, those where `row + col` is odd. Black starts on rows 0 to 2 and moves
  first, towards higher rows; white starts on rows 5 to 7 and moves towards lower rows.
- A man moves one square diagonally forward to an empty square. A king (crowned on reaching the far row) moves
  one square diagonally in any direction.
- A capture jumps diagonally over an adjacent opponent piece to the empty square just beyond, and removes it. Men
  capture forward only; kings in any direction. **Capturing is compulsory**: if any capture is available, the
  player must capture. A capture continues with further jumps by the same piece as long as it can jump again.
- A man that reaches the far row is crowned, and the move ends there.
- A player who cannot move loses. Show whose turn it is, the legal moves of a selected piece, and a New game button.

## Required game logic: `src/logic.ts`

All rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must use them.
They must not touch the DOM.

```ts
export type Piece = 'b' | 'w' | 'B' | 'W' | null;   // lower case: a man; upper case: a king
export interface Game { board: Piece[][]; turn: 'b' | 'w' }   // board[row][col], 8 x 8
export interface Move { path: [number, number][] }   // the start square, then every square the piece lands on

export function newGame(): Game;
export function legalMoves(game: Game): Move[];
export function play(game: Game, move: Move): Game;
```

- `newGame()`: black men on every dark square of rows 0-2, white men on every dark square of rows 5-7, `turn` = `'b'`.
- `legalMoves` lists every legal move for the player to move (any order). A simple move has a path of two squares.
  A capture lists the start and every landing square, and must include every further jump the piece can make: a
  capture that could continue is not a legal move on its own. When any capture exists, only captures are listed.
- `play` returns a **new** game (it must not change `game`) with the move made, captured pieces removed, a man
  crowned if it ended on the far row, and the turn passed. A move that is not in `legalMoves` returns the **same
  game object**.
