# Blackjack

A browser blackjack game: one player against the dealer, with a shuffled 52-card deck.

- The player and the dealer each get two cards; one dealer card stays face down. The player can Hit (take a
  card) or Stand. Going over 21 is a bust and loses at once.
- When the player stands, the dealer reveals their card and draws by the house rule below, then the hands are
  compared. A two-card 21 is a blackjack. Show both hands with their totals, the outcome, a running balance of
  chips (start with 100, bet 10 a hand, blackjack pays 15), and a Deal button.

## Required game logic: `src/logic.ts`

All game rules must live in `src/logic.ts` as pure functions with exactly these named exports. The page must
use them (the page shuffles and deals). They must not touch the DOM. Cards are strings by rank only: `'2'` to
`'10'`, `'J'`, `'Q'`, `'K'`, `'A'`.

```ts
export function handValue(cards: string[]): { total: number; soft: boolean };
export function isBlackjack(cards: string[]): boolean;
export function dealerShouldHit(cards: string[]): boolean;
export function outcome(player: string[], dealer: string[]): 'blackjack' | 'win' | 'lose' | 'push';
```

- `handValue`: number cards count their number, `J`, `Q` and `K` count 10, and each `A` counts 11 unless that
  would take the total over 21, in which case it counts 1. `soft` is `true` when an ace is being counted as 11.
- `isBlackjack` is `true` for exactly two cards totalling 21.
- `dealerShouldHit` is the house rule: the dealer hits on any total below 17, and also on a **soft** 17; the
  dealer stands on a hard 17 and above.
- `outcome` compares finished hands, in this order: player bust is `'lose'`; player blackjack against a dealer
  without blackjack is `'blackjack'`; both blackjack is `'push'`; dealer blackjack against a player without one
  is `'lose'`; dealer bust is `'win'`; otherwise the higher total wins (`'win'` or `'lose'`) and equal totals
  are `'push'`.
