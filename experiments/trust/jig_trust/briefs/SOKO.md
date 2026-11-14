# Box pusher

A browser box-pushing puzzle game with at least three built-in levels.

- The player moves with the arrow keys around a grid of walls and floor. Moving into a box pushes it one cell,
  but only if the cell beyond the box is floor (or a goal) with no box on it. The player cannot walk through
  walls or push two boxes at once.
- A level is solved when every box is on a goal. Show the move count, an Undo button, a Restart level button,
  and a Next level button once solved.

## Required game logic: `src/logic.ts`

All game rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must
use them. They must not touch the DOM.

Levels are written as strings, one per row: `'#'` wall, `' '` floor, `'.'` goal, `'$'` box, `'*'` box on a goal,
`'@'` player, `'+'` player on a goal. All rows of a level have the same length.

```ts
export interface State {
  walls: boolean[][];          // [row][col]
  goals: boolean[][];
  boxes: boolean[][];
  player: { row: number; col: number };
  moves: number;
}
export type Dir = 'up' | 'down' | 'left' | 'right';

export function parse(level: string[]): State;
export function move(state: State, dir: Dir): State;
export function isSolved(state: State): boolean;
export function render(state: State): string[];
```

- `parse` reads a level; `moves` starts at 0.
- `move` returns a **new** state (it must not change `state`) after one step in `dir`, pushing a box if there is
  one and it can move. `moves` goes up by one for every successful step. If the step is blocked (a wall, or a box
  that cannot move), it returns the **same `state` object**.
- `isSolved` is `true` when every box is on a goal.
- `render` writes the state back in the same characters as `parse` reads, so `render(parse(level))` equals
  `level`.
