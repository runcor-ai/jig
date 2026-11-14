import {
  BALL_SIZE,
  BASE_BALL_SPEED,
  FIELD_HEIGHT,
  FIELD_WIDTH,
  PADDLE_HEIGHT,
} from './constants';
import type { Command, GameState, Serve } from './types';

export function resetBall(dir: 1 | -1, angle: number): GameState['ball'] {
  return {
    x: FIELD_WIDTH / 2 - BALL_SIZE / 2,
    y: FIELD_HEIGHT / 2 - BALL_SIZE / 2,
    vx: dir * BASE_BALL_SPEED * Math.cos(angle),
    vy: BASE_BALL_SPEED * Math.sin(angle),
  };
}

export function createInitialState(serve: Serve = { angle: 0, dir: 1 }): GameState {
  const mid = (FIELD_HEIGHT - PADDLE_HEIGHT) / 2;
  return {
    phase: 'ready',
    winner: null,
    playerScore: 0,
    computerScore: 0,
    player: { y: mid },
    ai: { y: mid, targetY: FIELD_HEIGHT / 2, timer: 0 },
    ball: resetBall(serve.dir ?? 1, serve.angle),
  };
}

export function applyCommand(state: GameState, command: Command, serve?: Serve): GameState {
  if (command === 'restart') return createInitialState(serve);
  switch (state.phase) {
    case 'ready':
      return { ...state, phase: 'playing' };
    case 'playing':
      return { ...state, phase: 'paused' };
    case 'paused':
      return { ...state, phase: 'playing' };
    default:
      return state;
  }
}
