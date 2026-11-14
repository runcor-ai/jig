import { describe, expect, it } from 'vitest'
import { createInitialState, placeFood, queueDirection, step, tickInterval, togglePause, type GameState } from './logic'
import { mapKey } from './keys'

const rng0 = () => 0
const mk = (o: Partial<GameState>): GameState => ({ ...createInitialState(rng0), ...o })

describe('R-01 initial state', () => {
  it('has the right shape', () => {
    const s = createInitialState(rng0)
    expect(s.gridSize).toBe(20)
    expect(s.snake).toEqual([{ x: 11, y: 10 }, { x: 10, y: 10 }, { x: 9, y: 10 }])
    expect(s.direction).toBe('right')
    expect(s.score).toBe(0)
    expect(s.status).toBe('running')
    expect(s.food).not.toBeNull()
    expect(s.snake.some((p) => p.x === s.food!.x && p.y === s.food!.y)).toBe(false)
  })
})

describe('R-02 movement', () => {
  it('moves right and frees the tail', () => {
    const s = step(createInitialState(rng0), rng0)
    expect(s.snake[0]).toEqual({ x: 12, y: 10 })
    expect(s.snake).toHaveLength(3)
    expect(s.snake.some((p) => p.x === 9 && p.y === 10)).toBe(false)
  })
  it.each([
    ['up', 0, -1],
    ['down', 0, 1],
  ] as const)('moves %s', (dir, dx, dy) => {
    const s = step(queueDirection(createInitialState(rng0), dir), rng0)
    expect(s.snake[0]).toEqual({ x: 11 + dx, y: 10 + dy })
  })
  it('moves left (from a vertical heading)', () => {
    let s = step(queueDirection(createInitialState(rng0), 'up'), rng0)
    s = step(queueDirection(s, 'left'), rng0)
    expect(s.snake[0]).toEqual({ x: 10, y: 9 })
  })
})

describe('R-03 steering', () => {
  it('ignores a reverse', () => {
    const s = queueDirection(createInitialState(rng0), 'left')
    expect(step(s, rng0).direction).toBe('right')
  })
  it('double turn between ticks cannot reverse', () => {
    let s = createInitialState(rng0)
    s = queueDirection(s, 'up')
    s = queueDirection(s, 'left') // validated against last executed (right) -> a reverse, ignored
    s = step(s, rng0)
    expect(s.direction).toBe('up')
    expect(s.status).toBe('running')
  })
  it('maps keys', () => {
    expect(mapKey('ArrowUp')).toEqual({ type: 'dir', dir: 'up' })
    expect(mapKey('W')).toEqual({ type: 'dir', dir: 'up' })
    expect(mapKey('s')).toEqual({ type: 'dir', dir: 'down' })
    expect(mapKey('ArrowLeft')).toEqual({ type: 'dir', dir: 'left' })
    expect(mapKey('D')).toEqual({ type: 'dir', dir: 'right' })
    expect(mapKey(' ')).toEqual({ type: 'pause' })
    expect(mapKey('x')).toBeNull()
  })
})

describe('R-04 food', () => {
  it('grows and scores', () => {
    const s = mk({ food: { x: 12, y: 10 } })
    const n = step(s, rng0)
    expect(n.snake).toHaveLength(4)
    expect(n.score).toBe(10)
    expect(n.food).not.toBeNull()
    expect(n.snake.some((p) => p.x === n.food!.x && p.y === n.food!.y)).toBe(false)
  })
  it('placeFood uses rng over free cells', () => {
    expect(placeFood([{ x: 0, y: 0 }], 3, () => 0)).toEqual({ x: 1, y: 0 })
    expect(placeFood([{ x: 0, y: 0 }], 3, () => 0.999)).toEqual({ x: 2, y: 2 })
  })
  it('single free cell', () => {
    const snake = []
    for (let y = 0; y < 2; y++) for (let x = 0; x < 2; x++) if (!(x === 1 && y === 1)) snake.push({ x, y })
    expect(placeFood(snake, 2, () => 0.5)).toEqual({ x: 1, y: 1 })
  })
  it('returns null when full, and the game is won', () => {
    const full = [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 0, y: 1 }, { x: 1, y: 1 }]
    expect(placeFood(full, 2, rng0)).toBeNull()
    const s: GameState = { gridSize: 2, snake: [{ x: 0, y: 1 }, { x: 0, y: 0 }, { x: 1, y: 0 }], direction: 'down', pending: null, food: { x: 1, y: 1 }, score: 0, status: 'running' }
    // head (0,1) heading right eats food at (1,1); snake then fills the board
    const n = step(queueDirection(s, 'right'), rng0)
    expect(n.status).toBe('won')
  })
})

describe('R-05 speed', () => {
  it('derives interval from score', () => {
    expect(tickInterval(0)).toBe(150)
    expect(tickInterval(40)).toBe(150)
    expect(tickInterval(50)).toBe(135)
    expect(tickInterval(100)).toBe(120)
    expect(tickInterval(10000)).toBe(60)
  })
})

describe('R-06 game over', () => {
  it('hits walls on all sides', () => {
    const f = { x: 9, y: 9 }
    expect(step(mk({ snake: [{ x: 19, y: 5 }, { x: 18, y: 5 }], direction: 'right', food: f }), rng0).status).toBe('over')
    expect(step(mk({ snake: [{ x: 0, y: 5 }, { x: 1, y: 5 }], direction: 'left', food: f }), rng0).status).toBe('over')
    expect(step(mk({ snake: [{ x: 5, y: 0 }, { x: 5, y: 1 }], direction: 'up', food: f }), rng0).status).toBe('over')
    expect(step(mk({ snake: [{ x: 5, y: 19 }, { x: 5, y: 18 }], direction: 'down', food: f }), rng0).status).toBe('over')
  })
  it('hits itself', () => {
    const snake = [{ x: 5, y: 5 }, { x: 5, y: 6 }, { x: 6, y: 6 }, { x: 6, y: 5 }, { x: 6, y: 4 }, { x: 5, y: 4 }]
    const s = mk({ snake, direction: 'up', food: { x: 0, y: 0 } })
    expect(step(queueDirection(s, 'right'), rng0).status).toBe('over')
  })
  it('allows moving into the vacating tail', () => {
    const snake = [{ x: 5, y: 5 }, { x: 5, y: 6 }, { x: 6, y: 6 }, { x: 6, y: 5 }]
    const s = mk({ snake, direction: 'up', food: { x: 0, y: 0 } })
    expect(step(queueDirection(s, 'right'), rng0).status).toBe('running')
  })
  it('over is a no-op', () => {
    const s = mk({ status: 'over' })
    expect(step(s, rng0)).toBe(s)
  })
})

describe('R-08 pause', () => {
  it('toggles and ignores over', () => {
    const s = createInitialState(rng0)
    const p = togglePause(s)
    expect(p.status).toBe('paused')
    expect(step(p, rng0)).toBe(p)
    expect(togglePause(p).status).toBe('running')
    const o = mk({ status: 'over' })
    expect(togglePause(o)).toBe(o)
  })
})
