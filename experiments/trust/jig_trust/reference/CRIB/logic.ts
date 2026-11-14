const ORD: Record<string, number> = { A: 1, T: 10, J: 11, Q: 12, K: 13 };
const ord = (c: string) => ORD[c[0]] ?? Number(c[0]);
const val = (c: string) => Math.min(ord(c), 10);

function subsets<T>(xs: T[]): T[][] {
  const out: T[][] = [];
  for (let m = 1; m < 1 << xs.length; m++) out.push(xs.filter((_, i) => (m >> i) & 1));
  return out;
}

export const fifteens = (cards: string[]) =>
  2 * subsets(cards).filter((s) => s.reduce((a, c) => a + val(c), 0) === 15).length;

export function pairs(cards: string[]): number {
  let n = 0;
  for (let i = 0; i < cards.length; i++) for (let j = i + 1; j < cards.length; j++) if (cards[i][0] === cards[j][0]) n += 2;
  return n;
}

export function runs(cards: string[]): number {
  const isRun = (s: string[]) => {
    if (s.length < 3) return false;
    const r = s.map(ord).sort((a, b) => a - b);
    return r.every((v, i) => i === 0 || v === r[i - 1] + 1);
  };
  for (let len = cards.length; len >= 3; len--) {
    const found = subsets(cards).filter((s) => s.length === len && isRun(s));
    if (found.length) return found.length * len;
  }
  return 0;
}

export function flush(hand: string[], starter: string, isCrib: boolean): number {
  const suit = hand[0][1];
  if (!hand.every((c) => c[1] === suit)) return 0;
  if (starter[1] === suit) return 5;
  return isCrib ? 0 : 4;
}

export const nobs = (hand: string[], starter: string) => (hand.some((c) => c[0] === 'J' && c[1] === starter[1]) ? 1 : 0);

export function score(hand: string[], starter: string, isCrib = false): number {
  const all = [...hand, starter];
  return fifteens(all) + pairs(all) + runs(all) + flush(hand, starter, isCrib) + nobs(hand, starter);
}
