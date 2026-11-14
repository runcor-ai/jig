// Per frame: [score or null, rolls used]
function frames(rolls: number[]): { score: number | null; done: boolean }[] {
  const out: { score: number | null; done: boolean }[] = [];
  let i = 0;
  for (let f = 0; f < 10; f++) {
    const a = rolls[i], b = rolls[i + 1], c = rolls[i + 2];
    if (a === undefined) { out.push({ score: null, done: false }); continue; }
    if (a === 10) {
      out.push({ score: b !== undefined && c !== undefined ? 10 + b + c : null,
                 done: f < 9 ? true : b !== undefined && c !== undefined });
      i += 1;
    } else if (b === undefined) {
      out.push({ score: null, done: false });
      i += 2;
    } else if (a + b === 10) {
      out.push({ score: c !== undefined ? 10 + c : null, done: f < 9 ? true : c !== undefined });
      i += 2;
    } else {
      out.push({ score: a + b, done: true });
      i += 2;
    }
  }
  return out;
}

export function frameScores(rolls: number[]): (number | null)[] {
  let total = 0;
  let open = true;
  return frames(rolls).map((fr) => {
    if (!open || fr.score === null) { open = false; return null; }
    total += fr.score;
    return total;
  });
}

export function score(rolls: number[]): number {
  const fs = frameScores(rolls).filter((x): x is number => x !== null);
  return fs.length ? fs[fs.length - 1] : 0;
}

export function isComplete(rolls: number[]): boolean {
  return frames(rolls).every((f) => f.done);
}
