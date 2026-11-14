import { useCallback, useEffect, useState } from 'react'
import { createInitialState, queueDirection, step, tickInterval, togglePause } from './game/logic'
import { mapKey } from './game/keys'

export function useSnakeGame() {
  const [state, setState] = useState(() => createInitialState(Math.random))
  const [best, setBest] = useState(0)
  const interval = tickInterval(state.score)
  const active = state.status === 'running' || state.status === 'paused'

  // Tick timer: only while running; re-created when the interval changes.
  useEffect(() => {
    if (state.status !== 'running') return
    const id = setInterval(() => setState((s) => step(s, Math.random)), interval)
    return () => clearInterval(id)
  }, [state.status, interval])

  // Key listener: removed on unmount and on game over.
  useEffect(() => {
    if (!active) return
    const onKey = (e: KeyboardEvent) => {
      const action = mapKey(e.key)
      if (!action) return
      e.preventDefault()
      if (action.type === 'pause') setState(togglePause)
      else setState((s) => queueDirection(s, action.dir))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [active])

  useEffect(() => {
    if (state.score > best) setBest(state.score)
  }, [state.score, best])

  const restart = useCallback(() => setState(createInitialState(Math.random)), [])
  const pause = useCallback(() => setState(togglePause), [])
  return { state, best, restart, pause }
}
