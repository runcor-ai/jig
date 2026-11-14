export type Category =
  | 'high card' | 'pair' | 'two pair' | 'three of a kind' | 'straight'
  | 'flush' | 'full house' | 'four of a kind' | 'straight flush';

const ORDER: Category[] = ['high card', 'pair', 'two pair', 'three of a kind', 'straight', 'flush', 'full house',
  'four of a kind', 'straight flush'];
const VAL: Record<string, number> = { T: 10, J: 11, Q: 12, K: 13, A: 14 };
const rank = (c: string) => VAL[c[0]] ?? Number(c[0]);

export function evaluate(hand: string[]): { category: Category; ranks: number[] } {
  const rs = hand.map(rank).sort((a, b) => b - a);
  const flush = hand.every((c) => c[1] === hand[0][1]);
  const uniq = [...new Set(rs)];
  let straightHigh = 0;
  if (uniq.length === 5) {
    if (rs[0] - rs[4] === 4) straightHigh = rs[0];
    else if (rs.join() === '14,5,4,3,2') straightHigh = 5;
  }
  if (straightHigh) return { category: flush ? 'straight flush' : 'straight', ranks: [straightHigh] };
  const counts = new Map<number, number>();
  rs.forEach((r) => counts.set(r, (counts.get(r) ?? 0) + 1));
  const groups = [...counts.entries()].sort((a, b) => b[1] - a[1] || b[0] - a[0]);
  const shape = groups.map((g) => g[1]).join('');
  const byGroup = groups.map((g) => g[0]);
  if (shape === '41') return { category: 'four of a kind', ranks: byGroup };
  if (shape === '32') return { category: 'full house', ranks: byGroup };
  if (flush) return { category: 'flush', ranks: rs };
  if (shape === '311') return { category: 'three of a kind', ranks: byGroup };
  if (shape === '221') return { category: 'two pair', ranks: byGroup };
  if (shape === '2111') return { category: 'pair', ranks: byGroup };
  return { category: 'high card', ranks: rs };
}

export function compare(a: string[], b: string[]): 1 | -1 | 0 {
  const x = evaluate(a), y = evaluate(b);
  const d = ORDER.indexOf(x.category) - ORDER.indexOf(y.category);
  if (d) return d > 0 ? 1 : -1;
  for (let i = 0; i < Math.max(x.ranks.length, y.ranks.length); i++) {
    const e = (x.ranks[i] ?? 0) - (y.ranks[i] ?? 0);
    if (e) return e > 0 ? 1 : -1;
  }
  return 0;
}

export function best(hands: string[][]): number[] {
  let win: number[] = [];
  hands.forEach((hand, i) => {
    if (!win.length) win = [i];
    else {
      const c = compare(hand, hands[win[0]]);
      if (c > 0) win = [i];
      else if (c === 0) win.push(i);
    }
  });
  return win;
}
