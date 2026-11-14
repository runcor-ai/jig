export type Mark = 'right' | 'present' | 'absent';
export interface Game { answer: string; guesses: string[]; maxGuesses: number }

export function mark(answer: string, guess: string): Mark[] {
  const out: Mark[] = Array(guess.length).fill('absent');
  const rest: string[] = [];
  [...guess].forEach((ch, i) => (ch === answer[i] ? (out[i] = 'right') : rest.push(answer[i])));
  [...guess].forEach((ch, i) => {
    if (out[i] === 'right') return;
    const k = rest.indexOf(ch);
    if (k !== -1) { out[i] = 'present'; rest.splice(k, 1); }
  });
  return out;
}

export const newGame = (answer: string, maxGuesses = 6): Game => ({ answer, guesses: [], maxGuesses });

export function status(g: Game): 'playing' | 'won' | 'lost' {
  if (g.guesses.includes(g.answer)) return 'won';
  return g.guesses.length >= g.maxGuesses ? 'lost' : 'playing';
}

export function guess(g: Game, word: string, allowed: string[]): Game {
  const w = word.toLowerCase();
  if (w.length !== 5 || !allowed.includes(w) || status(g) !== 'playing') return g;
  return { ...g, guesses: [...g.guesses, w] };
}

const RANK: Record<Mark, number> = { absent: 0, present: 1, right: 2 };

export function keyboard(g: Game): Record<string, Mark> {
  const out: Record<string, Mark> = {};
  for (const w of g.guesses) mark(g.answer, w).forEach((m, i) => {
    const ch = w[i];
    if (!(ch in out) || RANK[m] > RANK[out[ch]]) out[ch] = m;
  });
  return out;
}
