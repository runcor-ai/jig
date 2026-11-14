# Towers puzzle

A browser towers puzzle: discs of different sizes stacked on three pegs.

- The game starts with N discs (the player picks 3 to 7) stacked on the left peg, largest at the bottom.
- The player moves one top disc at a time to another peg by clicking the source peg, then the target peg. A disc
  may never be placed on a smaller disc.
- The puzzle is solved when every disc is on the right peg. Show the number of moves, the fewest moves possible
  (2^N - 1), a message when solved, and a Restart button.

## Required game logic: `src/logic.ts`

All game rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must
use them. They must not touch the DOM.

```ts
export interface Game { pegs: number[][]; moves: number }   // pegs[0..2], each listed bottom to top; disc n has size n

export function newGame(discs: number): Game;
export function canMove(game: Game, from: number, to: number): boolean;
export function move(game: Game, from: number, to: number): Game;
export function isSolved(game: Game): boolean;
export function fewestMoves(discs: number): number;
```

- `newGame(n)` puts discs `n, n-1, ..., 1` on peg 0 (bottom to top), with pegs 1 and 2 empty and `moves` 0.
- `canMove` is `true` when `from` and `to` are different pegs 0 to 2, `from` has a disc, and its top disc is
  smaller than the top disc of `to` (or `to` is empty).
- `move` returns a **new** game with the top disc moved and `moves` up by one (it must not change `game`). If the
  move is not allowed, it returns the **same `game` object**.
- `isSolved` is `true` when every disc is on peg 2. `fewestMoves(n)` is `2^n - 1`.
