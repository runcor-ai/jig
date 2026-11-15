import { createInitialState, type GameState, type Rng } from './state';

export function start(state: GameState): GameState {
  return state.phase === 'ready' ? { ...state, phase: 'playing' } : state;
}

export function togglePause(state: GameState): GameState {
  if (state.phase === 'playing') return { ...state, phase: 'paused' };
  if (state.phase === 'paused') return { ...state, phase: 'playing' };
  return state;
}

/** What Space does in each phase (ignored in 'serving' and 'over'). */
export function pressSpace(state: GameState): GameState {
  return state.phase === 'ready' ? start(state) : togglePause(state);
}

export function restart(rng?: Rng): GameState {
  return createInitialState(rng);
}
