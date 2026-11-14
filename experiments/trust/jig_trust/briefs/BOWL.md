# Bowling scorecard

A browser ten-pin bowling scorecard game. The player enters each roll (how many pins fell) with buttons 0 to
10, and the scorecard shows the ten frames with running totals as the game goes.

- Standard ten-pin scoring. A strike (all 10 pins with the first roll of a frame) scores 10 plus the next two
  rolls. A spare (all 10 pins over the two rolls of a frame) scores 10 plus the next roll. Otherwise a frame
  scores the pins knocked down.
- In the tenth frame, a strike or spare earns bonus rolls (up to three rolls in that frame).
- Only buttons for possible pin counts are enabled, and the game ends after the tenth frame. Show the total and
  a New game button.

## Required game logic: `src/logic.ts`

All scoring rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page
must use them. They must not touch the DOM. Inputs are always valid sequences of rolls.

```ts
export function score(rolls: number[]): number;
export function frameScores(rolls: number[]): (number | null)[];
export function isComplete(rolls: number[]): boolean;
```

- `score(rolls)` is the total of every frame whose score can already be worked out from `rolls` (a strike or
  spare counts only once its bonus rolls have been made).
- `frameScores(rolls)` always has 10 entries: the running total up to and including that frame, or `null` when
  that frame's score cannot be worked out yet. Once a frame is `null`, every later frame is `null`.
- `isComplete(rolls)` is `true` when all ten frames, including any tenth-frame bonus rolls, have been rolled.
