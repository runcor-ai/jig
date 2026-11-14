# Dice poker

A browser five-dice scoring game for one player, with thirteen scoring categories.

- Each turn the player rolls five dice, may hold any dice and re-roll the rest, up to three rolls in total, then
  must score the dice in one unused category. After thirteen turns the game ends.
- The scorecard shows every category with the score the current dice would get, the upper-section bonus and the
  grand total. Show a New game button.

## Required game logic: `src/logic.ts`

All scoring rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must
use them (the page rolls the dice). They must not touch the DOM. Dice are always five numbers from 1 to 6.

```ts
export type Category =
  | 'ones' | 'twos' | 'threes' | 'fours' | 'fives' | 'sixes'
  | 'threeOfAKind' | 'fourOfAKind' | 'fullHouse' | 'smallStraight' | 'largeStraight' | 'yahtzee' | 'chance';

export function scoreCategory(dice: number[], category: Category): number;
export function bestCategory(dice: number[], available: Category[]): Category;
export function upperBonus(upperTotal: number): number;
```

- `ones` to `sixes`: the sum of the dice showing that number.
- `threeOfAKind` / `fourOfAKind`: the sum of all five dice if at least three / four show the same number, else 0.
- `fullHouse`: 25 if the dice are three of one number and two of another (five of a kind is **not** a full
  house), else 0.
- `smallStraight`: 30 if the dice include four numbers in sequence (1-2-3-4, 2-3-4-5 or 3-4-5-6), else 0.
- `largeStraight`: 40 if the dice are five numbers in sequence (1-2-3-4-5 or 2-3-4-5-6), else 0.
- `yahtzee`: 50 if all five dice are the same, else 0. `chance`: the sum of all five dice.
- `bestCategory(dice, available)` returns the category in `available` with the highest score for these dice;
  ties go to the one listed first in `available`.
- `upperBonus(upperTotal)` is 35 when the upper-section total is 63 or more, else 0.
