import type { Direction } from './logic'

export type KeyAction = { type: 'dir'; dir: Direction } | { type: 'pause' } | null

const DIRS: Record<string, Direction> = {
  arrowup: 'up', w: 'up',
  arrowdown: 'down', s: 'down',
  arrowleft: 'left', a: 'left',
  arrowright: 'right', d: 'right',
}

export function mapKey(key: string): KeyAction {
  if (key === ' ' || key === 'Spacebar') return { type: 'pause' }
  const dir = DIRS[key.toLowerCase()]
  return dir ? { type: 'dir', dir } : null
}
