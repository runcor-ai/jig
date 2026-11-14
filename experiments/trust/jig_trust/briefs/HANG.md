# Hangman

A browser word-guessing game.

- The page picks a secret word from a built-in list of at least 20 words and shows one blank per letter.
- The player guesses one letter at a time with on-screen letter buttons or the keyboard. Correct letters fill
  in every place they occur; wrong letters count as misses, and a drawing grows with each miss.
- The player wins by finding every letter, and loses after 6 misses (then the word is shown). Letters already
  guessed are disabled. Show a New game button.

## Required game logic: `src/logic.ts`

All game rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must
use them (the page chooses the word and passes it in). They must not touch the DOM.

```ts
export interface Game { word: string; guessed: string[]; maxMisses: number }

export function newGame(word: string, maxMisses?: number): Game;   // default 6
export function guess(game: Game, letter: string): Game;
export function masked(game: Game): string;
export function misses(game: Game): number;
export function status(game: Game): 'playing' | 'won' | 'lost';
```

- `newGame(word, maxMisses = 6)` stores the word in lower case, with no guesses yet.
- `guess(game, letter)` returns a **new** game (it must not change `game`) with the letter added, lower-cased, to
  `guessed`. Guessing is case-insensitive. If `letter` is not a single letter a to z, was already guessed, or
  the game is over, it returns the **same `game` object**.
- `masked(game)` shows each letter of the word that has been guessed and `_` for the others, separated by single
  spaces: the word `cat` with `a` guessed is `"_ a _"`.
- `misses(game)` is the number of guessed letters that are not in the word.
- `status(game)` is `'won'` when every letter of the word is guessed, `'lost'` when `misses` reaches
  `maxMisses`, otherwise `'playing'`.
