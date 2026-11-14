# Reversi

A browser Reversi game for two players on one screen, black against white, on an 8 x 8 board.

- The game starts with four discs in the centre. Black moves first.
- A move places a disc so that it brackets one or more straight lines of the opponent's discs (across, up and
  down, or diagonally) between the new disc and another disc of the mover's colour; every bracketed disc in every
  such line is flipped. A move that flips nothing is not allowed.
- If the player to move has no legal move, they pass and the other player moves again. The game ends when neither
  player can move. Show the legal moves, both scores, whose turn it is, the winner, and a New game button.

## Required game logic: `src/logic.ts`

All rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must use them.
They must not touch the DOM.

```ts
export type Disc = 'B' | 'W';
export interface Game { board: (Disc | null)[][]; turn: Disc }   // board[row][col], 8 x 8

export function newGame(): Game;
export function legalMoves(game: Game): [number, number][];
export function play(game: Game, row: number, col: number): Game;
export function score(game: Game): { B: number; W: number };
export function isOver(game: Game): boolean;
```

- `newGame()` has white at `(3, 3)` and `(4, 4)`, black at `(3, 4)` and `(4, 3)`, and `turn` = `'B'`.
- `legalMoves` lists every `[row, col]` where the player to move may play, in row-then-column order.
- `play` returns a **new** game (it must not change `game`) with the disc placed and every bracketed line flipped.
  Then the turn passes to the opponent if the opponent has a legal move; otherwise it stays with the player who
  just moved. An illegal move (occupied, outside the board, or flipping nothing) returns the **same game object**.
- `score` counts each colour's discs. `isOver` is `true` when neither player has a legal move.
