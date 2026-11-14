export type Phase = 'ready' | 'playing' | 'paused' | 'gameover';
export type Winner = 'player' | 'computer' | null;

export interface Input {
  up: boolean;
  down: boolean;
}

/** Injected serve: angle in radians; dir (1 = right, -1 = left) optional. */
export interface Serve {
  angle: number;
  dir?: 1 | -1;
}

export interface AIState {
  y: number;
  targetY: number;
  timer: number;
}

export interface GameState {
  phase: Phase;
  winner: Winner;
  playerScore: number;
  computerScore: number;
  player: { y: number };
  ai: AIState;
  ball: { x: number; y: number; vx: number; vy: number };
}

export type Command = 'toggle' | 'restart';
