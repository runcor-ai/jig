import { useCallback, useRef, useState, type CSSProperties } from 'react';
import { HEIGHT, WIDTH } from '../game/constants';
import { pressSpace, restart } from '../game/controls';
import { createInitialState, type GameState, type Rng } from '../game/state';
import { step } from '../game/step';
import { useGameLoop } from '../hooks/useGameLoop';
import { useKeyboard } from '../hooks/useKeyboard';

export interface GameProps {
  initialState?: GameState;
  rng?: Rng;
}

const box = (r: { x: number; y: number; width: number; height: number }): CSSProperties => ({
  position: 'absolute',
  left: r.x,
  top: r.y,
  width: r.width,
  height: r.height,
  background: '#fff',
});

const overlay: CSSProperties = {
  position: 'absolute',
  left: 0,
  right: 0,
  top: 140,
  textAlign: 'center',
  fontSize: 28,
};

export function Game({ initialState, rng = Math.random }: GameProps) {
  const stateRef = useRef<GameState>(initialState ?? createInitialState(rng));
  const [state, setState] = useState<GameState>(stateRef.current);

  const commit = useCallback((next: GameState) => {
    if (next !== stateRef.current) {
      stateRef.current = next;
      setState(next);
    }
  }, []);

  const { inputRef, direction } = useKeyboard(() => commit(pressSpace(stateRef.current)));
  useGameLoop((dt) => commit(step(stateRef.current, inputRef.current, dt, rng)));

  const { phase, left, right, ball, scores, winner } = state;

  return (
    <div style={{ width: WIDTH, margin: '20px auto', textAlign: 'center' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 32, padding: '0 40px' }}>
        <span>
          You: <span data-testid="score-player">{scores.player}</span>
        </span>
        <span>
          Computer: <span data-testid="score-computer">{scores.computer}</span>
        </span>
      </div>
      <div
        data-testid="playfield"
        data-input={direction}
        style={{ position: 'relative', width: WIDTH, height: HEIGHT, background: '#000', border: '1px solid #666', boxSizing: 'content-box' }}
      >
        <div data-testid="left-paddle" style={box(left)} />
        <div data-testid="right-paddle" style={box(right)} />
        <div data-testid="ball" style={box(ball)} />
        {phase === 'ready' && <div style={overlay}>Press Space to start</div>}
        {phase === 'paused' && <div style={overlay}>Paused</div>}
        {phase === 'over' && (
          <div style={overlay}>
            <div>{winner === 'player' ? 'You win!' : 'Computer wins'}</div>
            <button style={{ marginTop: 16, fontSize: 20 }} onClick={() => commit(restart(rng))}>
              Restart
            </button>
          </div>
        )}
      </div>
      <p style={{ color: '#aaa' }}>W/S or Up/Down to move. Space to start, pause and resume.</p>
    </div>
  );
}
