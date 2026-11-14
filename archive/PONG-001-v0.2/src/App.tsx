import { useCallback, useRef, useState } from 'react';
import { Playfield } from './components/Playfield';
import { createInitialState, step, type GameState } from './game/logic';
import { useGameLoop } from './hooks/useGameLoop';
import { useKeyboard } from './hooks/useKeyboard';

export default function App({ initialState }: { initialState?: GameState }) {
  const stateRef = useRef<GameState>(initialState ?? createInitialState());
  const [state, setState] = useState<GameState>(stateRef.current);

  const update = useCallback((next: GameState) => {
    stateRef.current = next;
    setState(next);
  }, []);

  const togglePause = useCallback(() => {
    const cur = stateRef.current;
    if (cur.status === 'playing') update({ ...cur, status: 'paused' });
    else if (cur.status === 'paused') update({ ...cur, status: 'playing' });
  }, [update]);

  const { getDirection } = useKeyboard(togglePause);

  const tick = useCallback(
    (dt: number) => {
      update(step(stateRef.current, { dir: getDirection() }, dt));
    },
    [getDirection, update],
  );

  useGameLoop(tick, state.status === 'playing');

  const restart = () => update(createInitialState(Math.random() < 0.5 ? -1 : 1));

  return (
    <div style={{ fontFamily: 'sans-serif', textAlign: 'center', color: '#222' }}>
      <h1>Pong</h1>
      <div style={{ display: 'inline-block' }}>
        <Playfield state={state} />
      </div>
      <p data-testid="status">{state.status}</p>
      <p>Move with W/S or the Up/Down arrow keys. Space pauses. First to 10 wins.</p>
      <button type="button" onClick={restart}>
        Restart
      </button>
    </div>
  );
}
