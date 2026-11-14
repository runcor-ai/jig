import { useCallback, useState } from 'react';
import type { CSSProperties } from 'react';
import { applyCommand, createInitialState } from '../game/state';
import { step } from '../game/step';
import type { GameState, Serve } from '../game/types';
import { useGameLoop } from '../hooks/useGameLoop';
import { useKeyboard } from '../hooks/useKeyboard';
import { Playfield } from './Playfield';

const randomServe = (): Serve => ({ angle: (Math.random() * 2 - 1) * (Math.PI / 6) });

const overlay: CSSProperties = {
  position: 'absolute',
  inset: 0,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 12,
  color: '#fff',
  fontSize: 28,
};

export function Game({ initialState }: { initialState?: GameState }) {
  const [state, setState] = useState<GameState>(
    () => initialState ?? createInitialState(randomServe()),
  );

  const input = useKeyboard(() => setState((s) => applyCommand(s, 'toggle')));
  const onTick = useCallback(
    (dt: number) => {
      const serve = randomServe();
      setState((s) => step(s, input.current, dt, serve));
    },
    [input],
  );
  useGameLoop(onTick, state.phase === 'playing');

  return (
    <div style={{ fontFamily: 'monospace', color: '#fff', width: 800 }}>
      <div style={{ display: 'flex', justifyContent: 'space-around', fontSize: 40 }}>
        <span data-testid="player-score">{state.playerScore}</span>
        <span data-testid="computer-score">{state.computerScore}</span>
      </div>
      <Playfield state={state}>
        {state.phase === 'ready' && (
          <div style={overlay}>
            <span>Press Space to start</span>
          </div>
        )}
        {state.phase === 'paused' && (
          <div style={overlay}>
            <span>Paused</span>
          </div>
        )}
        {state.phase === 'gameover' && (
          <div style={overlay}>
            <span>{state.winner === 'player' ? 'You win!' : 'Computer wins'}</span>
            <button onClick={() => setState((s) => applyCommand(s, 'restart', randomServe()))}>
              Restart
            </button>
          </div>
        )}
      </Playfield>
    </div>
  );
}
