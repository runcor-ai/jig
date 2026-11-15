const TABLE = [0, 100, 300, 500, 800];

export function scoreForLines(n: number): number {
  return TABLE[n] ?? 0;
}

export function levelForRows(rows: number): number {
  return Math.floor(rows / 10) + 1;
}

export function gravityMs(level: number): number {
  return Math.max(100, 1000 - (level - 1) * 100);
}
