import {
  BASE_INTERVAL,
  FOOD_PER_LEVEL,
  FOOD_SCORE,
  GRID_SIZE,
  INTERVAL_STEP,
  MIN_INTERVAL,
  type Direction,
  type GameState,
  type Point,
  type Rng,
} from './types'

const DELTAS: Record<Direction, Point> = {
  up: { x: 0, y: -1 },
  down: { x: 0, y: 1 },
  left: { x: -1, y: 0 },
  right: { x: 1, y: 0 },
}
const OPPOSITE: Record<Direction, Direction> = {
  up: 'down',
  down: 'up',
  left: 'right',
  right: 'left',
}

const same = (a: Point, b: Point) => a.x === b.x && a.y === b.y

export function placeFood(snake: Point[], rng: Rng, gridSize = GRID_SIZE): Point | null {
  const taken = new Set(snake.map((p) => p.y * gridSize + p.x))
  const free: Point[] = []
  for (let y = 0; y < gridSize; y++) {
    for (let x = 0; x < gridSize; x++) {
      if (!taken.has(y * gridSize + x)) free.push({ x, y })
    }
  }
  if (free.length === 0) return null
  const i = Math.min(free.length - 1, Math.floor(rng() * free.length))
  return free[i]
}

export function createInitialState(rng: Rng): GameState {
  const snake: Point[] = [
    { x: 10, y: 10 },
    { x: 9, y: 10 },
    { x: 8, y: 10 },
  ]
  return {
    gridSize: GRID_SIZE,
    snake,
    direction: 'right',
    lastMoved: 'right',
    food: placeFood(snake, rng),
    score: 0,
    foodEaten: 0,
    status: 'running',
  }
}

export function tickInterval(foodEaten: number): number {
  const level = Math.floor(Math.max(0, foodEaten) / FOOD_PER_LEVEL)
  return Math.max(MIN_INTERVAL, BASE_INTERVAL - level * INTERVAL_STEP)
}

export function changeDirection(state: GameState, dir: Direction): GameState {
  if (state.status !== 'running') return state
  if (dir === OPPOSITE[state.lastMoved] || dir === state.direction) return state
  return { ...state, direction: dir }
}

export function togglePause(state: GameState): GameState {
  if (state.status === 'running') return { ...state, status: 'paused' }
  if (state.status === 'paused') return { ...state, status: 'running' }
  return state
}

export function step(state: GameState, rng: Rng): GameState {
  if (state.status !== 'running') return state
  const d = DELTAS[state.direction]
  const head = state.snake[0]
  const next = { x: head.x + d.x, y: head.y + d.y }
  const n = state.gridSize
  const growing = state.food !== null && same(next, state.food)

  const outside = next.x < 0 || next.y < 0 || next.x >= n || next.y >= n
  // The tail cell is vacated this tick unless the snake grows.
  const body = growing ? state.snake : state.snake.slice(0, -1)
  if (outside || body.some((p) => same(p, next))) {
    return { ...state, lastMoved: state.direction, status: 'gameover' }
  }

  const snake = growing ? [next, ...state.snake] : [next, ...state.snake.slice(0, -1)]
  if (!growing) return { ...state, snake, lastMoved: state.direction }

  const food = placeFood(snake, rng, n)
  return {
    ...state,
    snake,
    lastMoved: state.direction,
    food,
    score: state.score + FOOD_SCORE,
    foodEaten: state.foodEaten + 1,
    // Board full: nowhere to put food, treat as game over.
    status: food === null ? 'gameover' : state.status,
  }
}
