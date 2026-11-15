import type { GameState } from '../game/game';

export default function Overlay({ state, onRestart }: { state: GameState; onRestart: () => void }) {
  if (state.status === 'paused') {
    return (
      <div className="overlay" data-testid="overlay">
        <h2>Paused</h2>
      </div>
    );
  }
  if (state.status === 'over') {
    return (
      <div className="overlay" data-testid="overlay">
        <h2>Game over</h2>
        <p>
          Final score: <strong data-testid="final-score">{state.score}</strong>
        </p>
        <button type="button" onClick={onRestart}>
          Restart
        </button>
      </div>
    );
  }
  return null;
}
