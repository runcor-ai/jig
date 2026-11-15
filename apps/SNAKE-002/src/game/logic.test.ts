import { describe, expect, it } from 'vitest'
import { changeDirection, createInitialState, placeFood, step, tickInterval, togglePause } from './logic'
import { keyToAction } from './keys'
import type { GameState, Point } from './types'

const rng0 = () => 0
const seeded = (seed: number) => () => {
  seed = (seed * 1664525 + 1013904223) % 4294967296
  return seed / 4294967296
}
const base = (over: Partial<GameState> = {}): GameState => ({
  ...createInitialState(rng0),
  food: { x: 0, y: 0 },
  ...over,
})

describe('R-01 initial state', () => {
  it('has the documented layout', () => {
    const s = createInitialState(seeded(1))
    expect(s.gridSize).toBe(20)
    expect(s.snake).toEqual([{ x: 10, y: 10 }, { x: 9, y: 10 }, { x: 8, y: 10 }])
    expect(s.direction).toBe('right')
    expect(s.score).toBe(0)
    expect(s.status).toBe('running')
    expect(s.food).not.toBeNull()
    expect(s.snake.some((p) => p.x === s.food!.x && p.y === s.food!.y)).toBe(false)
  })
})

describe('R-02 movement', () => {
  it('advances head and keeps length, without mutating', () => {
    const s = base()
    const copy = JSON.parse(JSON.stringify(s))
    const n = step(s, rng0)
    expect(n.snake).toEqual([{ x: 11, y: 10 }, { x: 10, y: 10 }, { x: 9, y: 10 }])
    expect(s).toEqual(copy)
  })
})

describe('R-03 direction', () => {
  it('rejects reversals', () => {
    const s = base()
    expect(changeDirection(s, 'left').direction).toBe('right')
    expect(changeDirection(s, 'up').direction).toBe('up')
    const up = base({ direction: 'up', lastMoved: 'up' })
    expect(changeDirection(up, 'down').direction).toBe('up')
  })
  it('two quick turns cannot reverse', () => {
    let s = base()
    s = changeDirection(s, 'up')
    s = changeDirection(s, 'left')
    expect(s.direction).toBe('up')
    expect(step(s, rng0).status).toBe('running')
  })
  it('maps keys', () => {
    const pairs: [string, string][] = [
      ['ArrowUp', 'up'], ['w', 'up'], ['W', 'up'],
      ['ArrowDown', 'down'], ['s', 'down'], ['S', 'down'],
      ['ArrowLeft', 'left'], ['a', 'left'], ['A', 'left'],
      ['ArrowRight', 'right'], ['d', 'right'], ['D', 'right'],
    ]
    for (const [k, d] of pairs) {
      expect(keyToAction(k)).toEqual({ type: 'direction', dir: d })
    }
    expect(keyToAction(' ')).toEqual({ type: 'pause' })
    expect(keyToAction('x')).toBeNull()
  })
})

describe('R-04 food placement', () => {
  it('never lands on the snake', () => {
    const snake: Point[] = [{ x: 3, y: 3 }, { x: 4, y: 3 }, { x: 5, y: 3 }]
    for (let i = 1; i <= 500; i++) {
      const f = placeFood(snake, seeded(i))!
      expect(snake.some((p) => p.x === f.x && p.y === f.y)).toBe(false)
      expect(f.x).toBeGreaterThanOrEqual(0)
      expect(f.x).toBeLessThan(20)
    }
  })
  it('finds the single free cell', () => {
    const snake: Point[] = []
    for (let y = 0; y < 20; y++) for (let x = 0; x < 20; x++) if (!(x === 7 && y === 13)) snake.push({ x, y })
    for (let i = 1; i <= 50; i++) expect(placeFood(snake, seeded(i))).toEqual({ x: 7, y: 13 })
    expect(placeFood([...snake, { x: 7, y: 13 }], rng0)).toBeNull()
  })
})

describe('R-05 eating', () => {
  it('grows, scores, counts and places new food', () => {
    const s = base({ food: { x: 11, y: 10 } })
    const n = step(s, seeded(3))
    expect(n.snake.length).toBe(4)
    expect(n.score).toBe(10)
    expect(n.foodEaten).toBe(1)
    expect(n.food).not.toEqual({ x: 11, y: 10 })
    expect(n.snake.some((p) => p.x === n.food!.x && p.y === n.food!.y)).toBe(false)
  })
})

describe('R-06 tickInterval', () => {
  it('shrinks to a floor', () => {
    expect(tickInterval(0)).toBe(150)
    expect(tickInterval(4)).toBe(150)
    expect(tickInterval(5)).toBe(135)
    expect(tickInterval(10)).toBe(120)
    expect(tickInterval(100)).toBe(60)
    let prev = Infinity
    for (let i = 0; i < 100; i++) {
      const t = tickInterval(i)
      expect(t).toBeLessThanOrEqual(prev)
      prev = t
    }
  })
})

describe('R-07 game over', () => {
  const at = (head: Point, dir: GameState['direction']) =>
    base({ snake: [head, { x: 5, y: 5 }, { x: 5, y: 6 }], direction: dir, lastMoved: dir })
  it('hits all four walls', () => {
    expect(step(at({ x: 19, y: 5 }, 'right'), rng0).status).toBe('gameover')
    expect(step(at({ x: 0, y: 5 }, 'left'), rng0).status).toBe('gameover')
    expect(step(at({ x: 5, y: 0 }, 'up'), rng0).status).toBe('gameover')
    expect(step(at({ x: 5, y: 19 }, 'down'), rng0).status).toBe('gameover')
  })
  it('hits its body', () => {
    const snake = [{ x: 5, y: 5 }, { x: 5, y: 6 }, { x: 6, y: 6 }, { x: 6, y: 5 }, { x: 6, y: 4 }]
    const s = base({ snake, direction: 'right', lastMoved: 'right' })
    expect(step(s, rng0).status).toBe('gameover')
  })
  it('may enter the vacating tail cell unless growing', () => {
    const snake = [{ x: 5, y: 5 }, { x: 5, y: 6 }, { x: 6, y: 6 }, { x: 6, y: 5 }]
    const s = base({ snake, direction: 'right', lastMoved: 'right' })
    expect(step(s, rng0).status).toBe('running')
    expect(step({ ...s, food: { x: 6, y: 5 } }, rng0).status).toBe('gameover')
  })
  it('is inert after game over', () => {
    const s = base({ status: 'gameover' })
    expect(step(s, rng0)).toBe(s)
  })
})

describe('R-10 pause', () => {
  it('toggles and ignores steps/directions when paused', () => {
    const s = base()
    const p = togglePause(s)
    expect(p.status).toBe('paused')
    expect(step(p, rng0)).toBe(p)
    expect(changeDirection(p, 'up')).toBe(p)
    expect(togglePause(p).status).toBe('running')
    const g = base({ status: 'gameover' })
    expect(togglePause(g)).toBe(g)
  })
})
