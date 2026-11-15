import type { Direction } from './types'

export type KeyAction = { type: 'direction'; dir: Direction } | { type: 'pause' } | null

const MAP: Record<string, Direction> = {
  ArrowUp: 'up', w: 'up', W: 'up',
  ArrowDown: 'down', s: 'down', S: 'down',
  ArrowLeft: 'left', a: 'left', A: 'left',
  ArrowRight: 'right', d: 'right', D: 'right',
}

export function keyToAction(key: string): KeyAction {
  if (key === ' ' || key === 'Spacebar') return { type: 'pause' }
  const dir = MAP[key]
  return dir ? { type: 'direction', dir } : null
}
