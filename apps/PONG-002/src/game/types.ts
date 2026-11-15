export type Phase = 'ready' | 'playing' | 'paused' | 'won'
export type Input = -1 | 0 | 1
export type Winner = 'player' | 'computer' | null

export interface Ball {
  x: number
  y: number
  vx: number
  vy: number
}

export interface GameState {
  width: number
  height: number
  playerY: number
  computerY: number
  ball: Ball
  playerScore: number
  computerScore: number
  phase: Phase
  winner: Winner
  /** seconds left before the ball starts moving after a point */
  serveDelay: number
  /** the y the AI is currently aiming at (refreshed every AI_REFRESH) */
  aiTargetY: number
  aiTimer: number
}
