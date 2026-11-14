// Pure game rules. No React or DOM imports.
export type Direction = 'up' | 'down' | 'left' | 'right'
export type Status = 'running' | 'paused' | 'over' | 'won'
export interface Point { x: number; y: number }
export type Rng = () => number

export interface GameState {
  gridSize: number
  /** head first */
  snake: Point[]
  /** direction used in the last executed tick */
  direction: Direction
  /** requested direction for the next tick (validated against `direction`) */
  pending: Direction | null
  food: Point | null
  score: number
  status: Status
}

export const GRID_SIZE = 20
const DELTA: Record<Direction, Point> = {
  up: { x: 0, y: -1 },
  down: { x: 0, y: 1 },
  left: { x: -1, y: 0 },
  right: { x: 1, y: 0 },
}
const OPPOSITE: Record<Direction, Direction> = { up: 'down', down: 'up', left: 'right', right: 'left' }

export const isReverse = (a: Direction, b: Direction): boolean => OPPOSITE[a] === b

export function placeFood(snake: Point[], size: number, rng: Rng): Point | null {
  const taken = new Set(snake.map((p) => p.y * size + p.x))
  const free: Point[] = []
  for (let y = 0; y < size; y++)
    for (let x = 0; x < size; x++) if (!taken.has(y * size + x)) free.push({ x, y })
  if (free.length === 0) return null
  const i = Math.min(free.length - 1, Math.max(0, Math.floor(rng() * free.length)))
  return free[i]
}

export function createInitialState(rng: Rng, size: number = GRID_SIZE): GameState {
  const y = size / 2
  const snake = [{ x: 11, y }, { x: 10, y }, { x: 9, y }]
  return { gridSize: size, snake, direction: 'right', pending: null, food: placeFood(snake, size, rng), score: 0, status: 'running' }
}

export function queueDirection(state: GameState, dir: Direction): GameState {
  if (state.status !== 'running' && state.status !== 'paused') return state
  if (dir === state.direction || isReverse(dir, state.direction)) return state
  return { ...state, pending: dir }
}

export function togglePause(state: GameState): GameState {
  if (state.status === 'running') return { ...state, status: 'paused' }
  if (state.status === 'paused') return { ...state, status: 'running' }
  return state
}

export function tickInterval(score: number): number {
  return Math.max(60, 150 - 15 * Math.floor(score / 50))
}

export function step(state: GameState, rng: Rng): GameState {
  if (state.status !== 'running') return state
  const dir = state.pending ?? state.direction
  const d = DELTA[dir]
  const head = { x: state.snake[0].x + d.x, y: state.snake[0].y + d.y }
  const n = state.gridSize
  const over: GameState = { ...state, direction: dir, pending: null, status: 'over' }
  if (head.x < 0 || head.y < 0 || head.x >= n || head.y >= n) return over
  const eats = !!state.food && state.food.x === head.x && state.food.y === head.y
  const kept = eats ? state.snake : state.snake.slice(0, -1) // tail vacates unless growing
  if (kept.some((p) => p.x === head.x && p.y === head.y)) return over
  const snake = [head, ...kept]
  if (!eats) return { ...state, snake, direction: dir, pending: null }
  const food = placeFood(snake, n, rng)
  return { ...state, snake, direction: dir, pending: null, score: state.score + 10, food, status: food ? 'running' : 'won' }
}
