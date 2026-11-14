const TABLE = [0, 100, 300, 500, 800];

export function scoreForLines(lines: number): number {
  return TABLE[lines] ?? 0;
}

export function levelForRows(rows: number): number {
  return 1 + Math.floor(rows / 10);
}

export function dropInterval(level: number): number {
  return Math.max(100, 1000 - (level - 1) * 80);
}
