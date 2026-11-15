import { useCallback, useEffect, useRef, useState } from 'react'
import { BALL_RADIUS, PADDLE_H, PADDLE_W, LEFT_PADDLE_X, RIGHT_PADDLE_X } from './game/constants'
import { initialState, restart, step, toggleSpace } from './game/logic'
import type { GameState } from './game/types'
import { useKeyboard } from './useKeyboard'

interface Props {
  /** optional starting state (used by tests) */
  initial?: GameState
  rng?: () => number
}

export function Game({ initial, rng = Math.random }: Props) {
  const stateRef = useRef<GameState>(initial ?? initialState())
  const [state, setState] = useState<GameState>(stateRef.current)
  const rngRef = useRef(rng)

  const commit = useCallback((s: GameState) => {
    stateRef.current = s
    setState(s)
  }, [])

  const inputRef = useKeyboard(() => commit(toggleSpace(stateRef.current)))

  const playing = state.phase === 'playing'
  useEffect(() => {
    if (!playing) return
    let id = 0
    let last: number | null = null
    const frame = (ts: number) => {
      const dt = last === null ? 0 : (ts - last) / 1000
      last = ts
      commit(step(stateRef.current, inputRef.current, dt, rngRef.current))
      id = requestAnimationFrame(frame)
    }
    id = requestAnimationFrame(frame)
    return () => cancelAnimationFrame(id)
  }, [playing, commit, inputRef])

  return (
    <div className="game">
      <div className="scores">
        <span>Player: <span data-testid="player-score">{state.playerScore}</span></span>
        <span>Computer: <span data-testid="computer-score">{state.computerScore}</span></span>
      </div>
      <div className="field-wrap" style={{ width: state.width, height: state.height }}>
        <svg data-testid="playfield" width={state.width} height={state.height}
          viewBox={`0 0 ${state.width} ${state.height}`}>
          <rect width={state.width} height={state.height} fill="#111" />
          <rect data-testid="player-paddle" x={LEFT_PADDLE_X} y={state.playerY}
            width={PADDLE_W} height={PADDLE_H} fill="#fff" />
          <rect data-testid="computer-paddle" x={RIGHT_PADDLE_X} y={state.computerY}
            width={PADDLE_W} height={PADDLE_H} fill="#fff" />
          <circle data-testid="ball" cx={state.ball.x} cy={state.ball.y} r={BALL_RADIUS} fill="#fff" />
        </svg>
        <div className="overlay">
          {state.phase === 'ready' && <p>Press Space to start</p>}
          {state.phase === 'paused' && <p>Paused – press Space to resume</p>}
          {state.phase === 'won' && (
            <>
              <p>{state.winner === 'player' ? 'You win!' : 'Computer wins!'}</p>
              <button onClick={() => commit(restart())}>Restart</button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
