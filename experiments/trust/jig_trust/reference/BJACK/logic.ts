const VAL: Record<string, number> = { J: 10, Q: 10, K: 10, A: 11 };

export function handValue(cards: string[]): { total: number; soft: boolean } {
  let total = 0, aces = 0;
  for (const c of cards) {
    if (c === 'A') aces++;
    total += VAL[c] ?? Number(c);
  }
  while (total > 21 && aces > 0) { total -= 10; aces--; }
  return { total, soft: aces > 0 };
}

export const isBlackjack = (cards: string[]) => cards.length === 2 && handValue(cards).total === 21;

export function dealerShouldHit(cards: string[]): boolean {
  const { total, soft } = handValue(cards);
  return total < 17 || (total === 17 && soft);
}

export function outcome(player: string[], dealer: string[]): 'blackjack' | 'win' | 'lose' | 'push' {
  const p = handValue(player).total, d = handValue(dealer).total;
  if (p > 21) return 'lose';
  const pb = isBlackjack(player), db = isBlackjack(dealer);
  if (pb && !db) return 'blackjack';
  if (pb && db) return 'push';
  if (db) return 'lose';
  if (d > 21) return 'win';
  return p > d ? 'win' : p < d ? 'lose' : 'push';
}
