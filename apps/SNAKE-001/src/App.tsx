import Board from './components/Board'
import { useSnakeGame } from './useSnakeGame'

export default function App() {
  const { state, best, restart } = useSnakeGame()
  const ended = state.status === 'over' || state.status === 'won'
  return (
    <div className="app">
      <h1>Snake</h1>
      <div className="scores">
        <span>Score: <b data-testid="score">{state.score}</b></span>
        <span>Best: <b data-testid="best">{best}</b></span>
      </div>
      <Board state={state} />
      {state.status === 'paused' && <div className="banner">Paused</div>}
      {ended && (
        <div className="banner" role="alert">
          <div>{state.status === 'won' ? 'You win!' : 'Game over'}</div>
          <div>Final score: <span data-testid="final-score">{state.score}</span></div>
          <button onClick={restart}>Restart</button>
        </div>
      )}
    </div>
  )
}
