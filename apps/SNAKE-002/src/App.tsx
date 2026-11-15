import { useEffect, useReducer, useState } from 'react'
import Board from './components/Board'
import { keyToAction } from './game/keys'
import {
  changeDirection,
  createInitialState,
  step,
  tickInterval,
  togglePause,
} from './game/logic'
import type { Direction, GameState } from './game/types'

type Action =
  | { type: 'tick' }
  | { type: 'dir'; dir: Direction }
  | { type: 'pause' }
  | { type: 'restart' }

function reducer(state: GameState, action: Action): GameState {
  switch (action.type) {
    case 'tick':
      return step(state, Math.random)
    case 'dir':
      return changeDirection(state, action.dir)
    case 'pause':
      return togglePause(state)
    case 'restart':
      return createInitialState(Math.random)
  }
}

export default function App() {
  const [state, dispatch] = useReducer(reducer, undefined, () => createInitialState(Math.random))
  const [best, setBest] = useState(0)

  useEffect(() => {
    setBest((b) => Math.max(b, state.score))
  }, [state.score])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const action = keyToAction(e.key)
      if (!action) return
      if (e.key.startsWith('Arrow') || action.type === 'pause') e.preventDefault()
      if (action.type === 'pause') dispatch({ type: 'pause' })
      else dispatch({ type: 'dir', dir: action.dir })
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => {
    if (state.status !== 'running') return
    const id = setTimeout(() => dispatch({ type: 'tick' }), tickInterval(state.foodEaten))
    return () => clearTimeout(id)
  }, [state])

  return (
    <div className="app">
      <h1>Snake</h1>
      <div className="panel">
        <span>Score: {state.score}</span>
        <span>Best: {Math.max(best, state.score)}</span>
      </div>
      <div className="board-wrap">
        <Board state={state} />
        {state.status === 'paused' && <div className="overlay">Paused</div>}
        {state.status === 'gameover' && (
          <div className="overlay">
            <div>Game over</div>
            <div>Final score: {state.score}</div>
            <button onClick={() => dispatch({ type: 'restart' })}>Restart</button>
          </div>
        )}
      </div>
    </div>
  )
}
