import { useEffect, useRef } from 'react'
import type { Input } from './game/types'

const UP = new Set(['w', 'arrowup'])
const DOWN = new Set(['s', 'arrowdown'])

/** Returns a ref holding the current input (-1/0/1); Space calls onToggle. */
export function useKeyboard(onToggle: () => void) {
  const input = useRef<Input>(0)
  const toggle = useRef(onToggle)
  toggle.current = onToggle

  useEffect(() => {
    // Track each direction by key so that two keys for one direction don't conflict.
    const heldUp = new Set<string>()
    const heldDown = new Set<string>()
    const update = () => {
      input.current = ((heldDown.size > 0 ? 1 : 0) - (heldUp.size > 0 ? 1 : 0)) as Input
    }
    const onKey = (pressed: boolean) => (e: KeyboardEvent) => {
      const k = e.key.toLowerCase()
      if (UP.has(k)) {
        if (pressed) heldUp.add(k)
        else heldUp.delete(k)
        e.preventDefault()
      } else if (DOWN.has(k)) {
        if (pressed) heldDown.add(k)
        else heldDown.delete(k)
        e.preventDefault()
      } else if (pressed && (e.key === ' ' || e.code === 'Space')) {
        e.preventDefault()
        if (!e.repeat) toggle.current()
      }
      update()
    }
    const kd = onKey(true)
    const ku = onKey(false)
    window.addEventListener('keydown', kd)
    window.addEventListener('keyup', ku)
    return () => {
      window.removeEventListener('keydown', kd)
      window.removeEventListener('keyup', ku)
    }
  }, [])

  return input
}
