import { useEffect, useMemo, useReducer, type Dispatch } from 'react';
import { createInitialState, createReducer, type Action, type GameState, type Random } from '../game/game';
import { dropInterval } from '../game/scoring';

export function keyToAction(e: KeyboardEvent): Action | null {
  switch (e.key) {
    case 'ArrowLeft': return { type: 'left' };
    case 'ArrowRight': return { type: 'right' };
    case 'ArrowDown': return { type: 'softDrop' };
    case 'ArrowUp': return e.repeat ? null : { type: 'rotate' };
    case ' ':
    case 'Spacebar': return e.repeat ? null : { type: 'hardDrop' };
    case 'p':
    case 'P': return e.repeat ? null : { type: 'togglePause' };
    default: return null;
  }
}

const PREVENT = new Set(['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', ' ', 'Spacebar']);

export function useGame(
  random: Random = Math.random,
  initialState?: GameState,
): { state: GameState; dispatch: Dispatch<Action> } {
  const reducer = useMemo(() => createReducer(random), [random]);
  const [state, dispatch] = useReducer(reducer, undefined, () => initialState ?? createInitialState(random));

  // Gravity: the timer is re-created whenever level or status changes.
  const { level, status } = state;
  useEffect(() => {
    if (status !== 'playing') return;
    const id = setInterval(() => dispatch({ type: 'tick' }), dropInterval(level));
    return () => clearInterval(id);
  }, [level, status]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (PREVENT.has(e.key)) e.preventDefault();
      const action = keyToAction(e);
      if (action) dispatch(action);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return { state, dispatch };
}
