import { useCallback, useRef, useState } from 'react';
import { Playfield } from './components/Playfield';
import { WIN_SCORE, type GameState } from './game/config';
import { createInitialState, pause, restart, startOrTogglePause, step } from './game/logic';
import { useGameLoop } from './hooks/useGameLoop';
import { useKeyboard } from './hooks/useKeyboard';

export default function App({ initialState }: { initialState?: GameState }) {
  const [state, setState] = useState<GameState>(() => initialState ?? createInitialState());
  const ref = useRef(state);

  const apply = useCallback((fn: (s: GameState) => GameState) => {
    const next = fn(ref.current);
    if (next !== ref.current) { ref.current = next; setState(next); }
  }, []);

  const input = useKeyboard(() => apply(startOrTogglePause));
  useGameLoop(
    (dt) => apply((s) => step(s, input.current, dt)),
    () => apply(pause),
  );

  return (
    <main style={{ fontFamily: 'sans-serif', textAlign: 'center', color: '#eee', background: '#111', minHeight: '100vh', padding: 16 }}>
      <h1>Pong</h1>
      <div style={{ fontSize: 32 }} aria-label="Score">
        Player <span data-testid="player-score">{state.playerScore}</span> – <span data-testid="ai-score">{state.aiScore}</span> Computer
      </div>
      <div style={{ position: 'relative', display: 'inline-block', maxWidth: '100%' }}>
        <Playfield state={state} />
        <div role="status" style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28, pointerEvents: 'none', color: '#ff0' }}>
          {state.status === 'ready' && <span>Press Space to start</span>}
          {state.status === 'paused' && <span>Paused – press Space to resume</span>}
          {state.status === 'over' && <span>{state.winner === 'player' ? 'You win!' : 'Computer wins!'}</span>}
        </div>
      </div>
      <div style={{ margin: 12 }}>
        <button type="button" onClick={() => apply(() => restart())}>Restart</button>
      </div>
      <p>Controls: ArrowUp / W = up, ArrowDown / S = down, Space = start / pause. First to {WIN_SCORE} points wins.</p>
    </main>
  );
}
