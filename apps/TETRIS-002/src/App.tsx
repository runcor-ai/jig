import { useCallback, useReducer, useRef, useState } from 'react';
import BoardView from './components/BoardView';
import Overlay from './components/Overlay';
import SidePanel from './components/SidePanel';
import { newGame, reduce } from './game/game';
import type { Action, GameState } from './game/game';
import { useGravity } from './hooks/useGravity';
import { useKeyboard } from './hooks/useKeyboard';

interface AppProps {
  rng?: () => number;
  initialState?: GameState;
}

export default function App({ rng = Math.random, initialState }: AppProps) {
  const rngRef = useRef(rng);
  rngRef.current = rng;
  const [state, rawDispatch] = useReducer(
    (s: GameState, a: Action) => reduce(s, a, rngRef.current),
    undefined,
    () => initialState ?? newGame(rng),
  );
  const [resetToken, setResetToken] = useState(0);

  const dispatch = useCallback((a: Action) => {
    if (a === 'softDrop') setResetToken((t) => t + 1);
    rawDispatch(a);
  }, []);

  useKeyboard(dispatch);
  useGravity(state.status, state.level, dispatch, resetToken);

  return (
    <main className="app">
      <h1>Falling Blocks</h1>
      <div className="game">
        <div className="well">
          <BoardView state={state} />
          <Overlay state={state} onRestart={() => dispatch('restart')} />
        </div>
        <SidePanel state={state} />
      </div>
      <p className="help">← → move · ↑ rotate · ↓ soft drop · Space hard drop · P pause</p>
    </main>
  );
}
