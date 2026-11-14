# Cribbage hand counter

A browser cribbage practice game: deal a four-card hand and a starter card, let the player enter what they think
the hand scores, then show the correct score broken down by fifteens, pairs, runs, flush and nobs. A Deal button
deals again; a checkbox scores the hand as the crib.

## Required game logic: `src/logic.ts`

All scoring rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must use
them (the page shuffles and deals). They must not touch the DOM.

A card is a string of rank then suit: ranks `A`, `2`-`9`, `T`, `J`, `Q`, `K`; suits `c`, `d`, `h`, `s`. For
fifteens an ace counts 1 and `T`, `J`, `Q`, `K` count 10. For runs the order is A, 2, ..., 10, J, Q, K (an ace is
low only; runs do not wrap from K to A).

```ts
export function fifteens(cards: string[]): number;
export function pairs(cards: string[]): number;
export function runs(cards: string[]): number;
export function flush(hand: string[], starter: string, isCrib: boolean): number;
export function nobs(hand: string[], starter: string): number;
export function score(hand: string[], starter: string, isCrib?: boolean): number;
```

- `fifteens`: 2 points for every distinct combination of cards (any size) whose values add up to 15.
- `pairs`: 2 points for every pair of cards of equal rank (so three of a kind scores 6 and four of a kind 12).
- `runs`: points for runs of three or more consecutive ranks, using the longest runs only. Each distinct
  combination of cards forming a longest run counts: 3-4-5 scores 3, 3-3-4-5 scores 6 (two runs of three),
  3-3-4-4-5 scores 12, and 2-3-4-5 scores 4 (not two runs of three).
- `flush(hand, starter, isCrib)`: the four hand cards all of one suit score 4, or 5 if the starter matches too.
  For the crib, only all five cards of one suit count (5); otherwise 0.
- `nobs`: 1 if the hand holds the jack of the starter's suit.
- `score(hand, starter, isCrib = false)` is the total, with fifteens, pairs and runs counted over all five cards.
