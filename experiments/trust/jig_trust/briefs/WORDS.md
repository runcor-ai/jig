# Five-letter word guess

A browser word-guessing game: find a hidden five-letter word in six guesses.

- The page picks the hidden word from a built-in list of at least 30 five-letter words. The player types a guess
  of five letters and presses Enter; guesses must be in the list.
- Each letter of a guess is marked: right letter in the right place, right letter in the wrong place, or not in
  the word. An on-screen keyboard shows the best mark each letter has had so far.
- The player wins by guessing the word, and loses after six wrong guesses (then the word is shown). Show a New
  game button. Use your own colours and layout.

## Required game logic: `src/logic.ts`

All game rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must
use them (the page picks the word and the list). They must not touch the DOM. Words are lower case.

```ts
export type Mark = 'right' | 'present' | 'absent';
export interface Game { answer: string; guesses: string[]; maxGuesses: number }

export function mark(answer: string, guess: string): Mark[];
export function newGame(answer: string, maxGuesses?: number): Game;    // default 6
export function guess(game: Game, word: string, allowed: string[]): Game;
export function status(game: Game): 'playing' | 'won' | 'lost';
export function keyboard(game: Game): Record<string, Mark>;
```

- `mark` gives one mark per letter of `guess`: `'right'` when it matches the answer's letter in that place;
  otherwise `'present'` if the letter is among the answer's letters not already matched, each answer letter used
  at most once, left to right; otherwise `'absent'`. For example, answer `apple` and guess `paper` give
  `present, present, right, present, absent`.
- `newGame` starts with no guesses.
- `guess(game, word, allowed)` returns a **new** game with `word` (lower-cased) added. If it is not five letters,
  not in `allowed`, or the game is over, it returns the **same `game` object**.
- `status` is `'won'` once a guess equals the answer, `'lost'` after `maxGuesses` wrong guesses, else `'playing'`.
- `keyboard` maps every guessed letter to its best mark so far (`right` beats `present` beats `absent`).
