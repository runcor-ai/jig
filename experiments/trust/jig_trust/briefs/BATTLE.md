# Sea battle

A browser sea-battle game: the player fires at a hidden fleet on a 10 x 10 grid.

- The page places a fleet of five ships at random (lengths 5, 4, 3, 3 and 2), each horizontal or vertical, always
  inside the grid and never overlapping.
- The player clicks cells to fire. Each shot shows a hit or a miss; when every cell of a ship is hit, that ship is
  sunk and its name is shown. The game is won when every ship is sunk. Show the number of shots and a New game
  button.

## Required game logic: `src/logic.ts`

All game rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must
use them (the page chooses the random fleet and passes it in). They must not touch the DOM.

```ts
export interface Ship { name: string; row: number; col: number; length: number; horizontal: boolean }
export interface Game { size: number; ships: Ship[]; shots: [number, number][] }   // shots as [row, col]

export function cells(ship: Ship): [number, number][];          // [row, col], from the ship's start
export function canPlace(size: number, ships: Ship[], ship: Ship): boolean;
export function newGame(size: number, ships: Ship[]): Game;
export function fire(game: Game, row: number, col: number): Game;
export function result(game: Game, row: number, col: number): 'miss' | 'hit' | 'sunk' | 'unknown';
export function isWon(game: Game): boolean;
```

- `cells(ship)` lists the ship's cells starting at `(row, col)`, going right when horizontal and down otherwise.
- `canPlace` is `true` when every cell of `ship` is inside a `size` x `size` grid and none overlaps a cell of
  `ships`. (Ships may sit next to each other.)
- `newGame` starts a game with no shots.
- `fire` returns a **new** game with the shot added (it must not change `game`). Firing outside the grid, at a
  cell already shot, or after the game is won returns the **same `game` object**.
- `result` describes a cell: `'unknown'` if it has not been shot, `'miss'` if it is empty, `'sunk'` if it belongs
  to a ship whose every cell has been shot, otherwise `'hit'`.
- `isWon` is `true` when every cell of every ship has been shot.
