export interface Game { word: string; guessed: string[]; maxMisses: number }

export function newGame(word: string, maxMisses = 6): Game {
  return { word: word.toLowerCase(), guessed: [], maxMisses };
}

export function misses(g: Game): number {
  return g.guessed.filter((c) => !g.word.includes(c)).length;
}

export function status(g: Game): 'playing' | 'won' | 'lost' {
  if ([...g.word].every((c) => g.guessed.includes(c))) return 'won';
  return misses(g) >= g.maxMisses ? 'lost' : 'playing';
}

export function guess(g: Game, letter: string): Game {
  const c = letter.toLowerCase();
  if (!/^[a-z]$/.test(c) || g.guessed.includes(c) || status(g) !== 'playing') return g;
  return { ...g, guessed: [...g.guessed, c] };
}

export function masked(g: Game): string {
  return [...g.word].map((c) => (g.guessed.includes(c) ? c : '_')).join(' ');
}
