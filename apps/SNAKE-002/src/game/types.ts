export const GRID_SIZE = 20
export const BASE_INTERVAL = 150
export const INTERVAL_STEP = 15
export const FOOD_PER_LEVEL = 5
export const MIN_INTERVAL = 60
export const FOOD_SCORE = 10

export interface Point {
  x: number
  y: number
}
export type Direction = 'up' | 'down' | 'left' | 'right'
export type Status = 'running' | 'paused' | 'gameover'
export type Rng = () => number

export interface GameState {
  gridSize: number
  /** Head is FIRST; the tail is last. */
  snake: Point[]
  /** Direction that the next tick will use. */
  direction: Direction
  /** Direction used by the last tick (reversal checks use this). */
  lastMoved: Direction
  food: Point | null
  score: number
  foodEaten: number
  status: Status
}
