export interface Game { secret: string[]; guesses: string[][]; maxTurns: number }

export function score(secret: string[], guess: string[]): { black: number; white: number } {
  let black = 0;
  const restS: string[] = [], restG: string[] = [];
  secret.forEach((s, i) => (s === guess[i] ? black++ : (restS.push(s), restG.push(guess[i]))));
  let white = 0;
  for (const g of restG) {
    const k = restS.indexOf(g);
    if (k !== -1) { white++; restS.splice(k, 1); }
  }
  return { black, white };
}

export function newGame(secret: string[], maxTurns = 10): Game {
  return { secret: secret.slice(), guesses: [], maxTurns };
}

export function status(g: Game): 'playing' | 'won' | 'lost' {
  if (g.guesses.some((x) => score(g.secret, x).black === g.secret.length)) return 'won';
  return g.guesses.length >= g.maxTurns ? 'lost' : 'playing';
}

export function guess(g: Game, x: string[]): Game {
  if (x.length !== g.secret.length || status(g) !== 'playing') return g;
  return { ...g, guesses: [...g.guesses, x.slice()] };
}
