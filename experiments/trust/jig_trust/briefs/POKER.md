# Poker hands

A browser poker-hand showdown: deal five cards to each of 2 to 4 players from a shuffled deck, show every hand
with its name, and announce the winner (or a split pot). A Deal button deals again.

## Required game logic: `src/logic.ts`

All rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must use them
(the page shuffles and deals). They must not touch the DOM.

A card is a string of rank then suit: ranks `2`-`9`, `T`, `J`, `Q`, `K`, `A`; suits `c`, `d`, `h`, `s` (for example
`'Th'`, `'As'`). Rank values are 2 to 14 (`A` = 14).

```ts
export type Category =
  | 'high card' | 'pair' | 'two pair' | 'three of a kind' | 'straight'
  | 'flush' | 'full house' | 'four of a kind' | 'straight flush';

export function evaluate(hand: string[]): { category: Category; ranks: number[] };
export function compare(a: string[], b: string[]): 1 | -1 | 0;
export function best(hands: string[][]): number[];
```

- `evaluate` takes five cards and returns the category and the tie-break `ranks`, highest first:
  - straight and straight flush: `[highest card]`, where A-2-3-4-5 is a straight with highest card 5;
  - four of a kind: `[the four's rank, kicker]`; full house: `[the three's rank, the pair's rank]`;
  - three of a kind: `[the three's rank, kickers high to low]`;
  - two pair: `[higher pair, lower pair, kicker]`; pair: `[the pair's rank, kickers high to low]`;
  - flush and high card: all five ranks, high to low.
- `compare(a, b)` is `1` if hand `a` wins, `-1` if `b` wins, `0` for a tie: the higher category wins; within a
  category, compare `ranks` element by element. Suits never break a tie.
- `best(hands)` returns the indexes of every winning hand, in ascending order (more than one for a tie).
