export type Category =
  | 'ones' | 'twos' | 'threes' | 'fours' | 'fives' | 'sixes'
  | 'threeOfAKind' | 'fourOfAKind' | 'fullHouse' | 'smallStraight' | 'largeStraight' | 'yahtzee' | 'chance';

const UPPER: Partial<Record<Category, number>> = { ones: 1, twos: 2, threes: 3, fours: 4, fives: 5, sixes: 6 };

export function scoreCategory(dice: number[], cat: Category): number {
  const sum = dice.reduce((a, b) => a + b, 0);
  const counts = [0, 0, 0, 0, 0, 0, 0];
  dice.forEach((d) => counts[d]++);
  const max = Math.max(...counts);
  const has = (seq: number[]) => seq.every((n) => counts[n] > 0);
  if (UPPER[cat]) return dice.filter((d) => d === UPPER[cat]).reduce((a, b) => a + b, 0);
  switch (cat) {
    case 'threeOfAKind': return max >= 3 ? sum : 0;
    case 'fourOfAKind': return max >= 4 ? sum : 0;
    case 'fullHouse': return counts.includes(3) && counts.includes(2) ? 25 : 0;
    case 'smallStraight': return has([1, 2, 3, 4]) || has([2, 3, 4, 5]) || has([3, 4, 5, 6]) ? 30 : 0;
    case 'largeStraight': return has([1, 2, 3, 4, 5]) || has([2, 3, 4, 5, 6]) ? 40 : 0;
    case 'yahtzee': return max === 5 ? 50 : 0;
    case 'chance': return sum;
  }
  return 0;
}

export function bestCategory(dice: number[], available: Category[]): Category {
  let best = available[0];
  for (const c of available) if (scoreCategory(dice, c) > scoreCategory(dice, best)) best = c;
  return best;
}

export const upperBonus = (t: number) => (t >= 63 ? 35 : 0);
