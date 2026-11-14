# Code breaker

A browser code-breaking game with coloured pegs.

- The page picks a secret code of 4 pegs, each one of 6 colours (red, green, blue, yellow, orange, purple);
  colours may repeat.
- The player has 10 turns. Each turn they build a guess of 4 pegs and submit it. The game marks it with black
  pegs (right colour in the right place) and white pegs (right colour in the wrong place).
- The player wins by guessing the code exactly, and loses after 10 wrong guesses (then the code is shown).
  Show every guess with its marks, and a New game button.

## Required game logic: `src/logic.ts`

All game rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must
use them (the page picks the secret code and passes it in). They must not touch the DOM. Colours are strings.

```ts
export function score(secret: string[], guess: string[]): { black: number; white: number };

export interface Game { secret: string[]; guesses: string[][]; maxTurns: number }
export function newGame(secret: string[], maxTurns?: number): Game;   // default 10
export function guess(game: Game, g: string[]): Game;
export function status(game: Game): 'playing' | 'won' | 'lost';
```

- `score`: `black` counts positions where the guess matches the secret. `white` counts the remaining pegs of the
  guess whose colour appears among the remaining (unmatched) pegs of the secret, each secret peg matching at
  most once. For example, secret `[r, r, g, b]` and guess `[r, g, r, r]` give 1 black and 2 white.
- `newGame` stores the secret with no guesses.
- `guess(game, g)` returns a **new** game (it must not change `game`) with `g` added to `guesses`. If `g` is not
  the same length as the secret, or the game is over, it returns the **same `game` object**.
- `status` is `'won'` once a guess equals the secret, `'lost'` when `maxTurns` guesses were made without
  winning, otherwise `'playing'`.
