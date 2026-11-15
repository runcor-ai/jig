import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { Game } from './Game'
import { initialState } from './game/logic'
import type { GameState } from './game/types'

let callbacks: Map<number, FrameRequestCallback>
let nextId: number
let cancelSpy: ReturnType<typeof vi.fn>

beforeEach(() => {
  callbacks = new Map()
  nextId = 1
  cancelSpy = vi.fn((id: number) => { callbacks.delete(id) })
  vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
    const id = nextId++
    callbacks.set(id, cb)
    return id
  })
  vi.stubGlobal('cancelAnimationFrame', cancelSpy)
})
afterEach(() => {
  vi.unstubAllGlobals()
})

function frame(ts: number) {
  const pending = [...callbacks.values()]
  callbacks.clear()
  act(() => pending.forEach((cb) => cb(ts)))
}
const key = (k: string, type: 'keyDown' | 'keyUp' = 'keyDown') =>
  act(() => { fireEvent[type](window, { key: k, code: k === ' ' ? 'Space' : k }) })
const space = () => key(' ')
const num = (id: string, attr: string) => Number(screen.getByTestId(id).getAttribute(attr))

describe('Game rendering', () => {
  it('renders the fixed-size playfield, start message and 0-0 scores', () => {
    render(<Game />)
    const field = screen.getByTestId('playfield')
    expect(field).toHaveAttribute('width', '800')
    expect(field).toHaveAttribute('height', '500')
    expect(screen.getByText('Press Space to start')).toBeInTheDocument()
    expect(screen.getByTestId('player-score')).toHaveTextContent('0')
    expect(screen.getByTestId('computer-score')).toHaveTextContent('0')
    expect(screen.queryByRole('button', { name: 'Restart' })).toBeNull()
  })
})

describe('Space phases and loop', () => {
  it('starts, pauses and resumes; ball moves only while playing', () => {
    render(<Game />)
    space()
    expect(screen.queryByText('Press Space to start')).toBeNull()
    frame(0)
    frame(16)
    const x1 = num('ball', 'cx')
    expect(x1).toBeGreaterThan(400)
    frame(32)
    const x2 = num('ball', 'cx')
    expect(x2).toBeGreaterThan(x1)

    space() // pause
    frame(48)
    frame(64)
    expect(num('ball', 'cx')).toBe(x2)

    space() // resume
    frame(80)
    frame(96)
    expect(num('ball', 'cx')).toBeGreaterThan(x2)
  })

  it('cancels the pending frame on unmount and on pause', () => {
    const { unmount } = render(<Game />)
    space()
    expect(callbacks.size).toBe(1)
    space()
    expect(cancelSpy).toHaveBeenCalledTimes(1)
    expect(callbacks.size).toBe(0)
    space()
    expect(callbacks.size).toBe(1)
    unmount()
    expect(cancelSpy).toHaveBeenCalledTimes(2)
    expect(callbacks.size).toBe(0)
  })
})

describe('keys', () => {
  const run = (down: string[], up: string[] = []) => {
    render(<Game />)
    space()
    frame(0)
    const y0 = num('player-paddle', 'y')
    down.forEach((k) => key(k))
    up.forEach((k) => key(k, 'keyUp'))
    frame(16)
    return num('player-paddle', 'y') - y0
  }
  it.each(['w', 'ArrowUp'])('%s moves up', (k) => {
    expect(run([k])).toBeLessThan(0)
  })
  it.each(['s', 'ArrowDown'])('%s moves down', (k) => {
    expect(run([k])).toBeGreaterThan(0)
  })
  it('opposing keys cancel out', () => {
    expect(run(['w', 's'])).toBe(0)
  })
  it('keyup stops movement', () => {
    expect(run(['w'], ['w'])).toBe(0)
  })
})

describe('score display, winner and restart', () => {
  const nearWin = (who: 'player' | 'computer'): GameState =>
    who === 'player'
      ? { ...initialState(), phase: 'playing', playerScore: 9, computerY: 0, ball: { x: 799, y: 400, vx: 600, vy: 0 } }
      : { ...initialState(), phase: 'playing', computerScore: 9, playerY: 0, ball: { x: 1, y: 400, vx: -600, vy: 0 } }

  it('updates the scores after a point', () => {
    const s: GameState = { ...initialState(), phase: 'playing', computerY: 0, ball: { x: 799, y: 400, vx: 600, vy: 0 } }
    render(<Game initial={s} rng={() => 0.5} />)
    frame(0)
    frame(16)
    expect(screen.getByTestId('player-score')).toHaveTextContent('1')
    expect(screen.getByTestId('computer-score')).toHaveTextContent('0')
  })

  it('shows "You win!" and Restart, and Restart resets', () => {
    render(<Game initial={nearWin('player')} rng={() => 0.5} />)
    frame(0)
    frame(16)
    expect(screen.getByText('You win!')).toBeInTheDocument()
    expect(screen.getByTestId('player-score')).toHaveTextContent('10')
    // space does nothing when won
    space()
    expect(screen.getByText('You win!')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Restart' }))
    expect(screen.getByTestId('player-score')).toHaveTextContent('0')
    expect(screen.getByTestId('computer-score')).toHaveTextContent('0')
    expect(screen.getByText('Press Space to start')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Restart' })).toBeNull()
    expect(screen.queryByText('You win!')).toBeNull()
  })

  it('shows "Computer wins!"', () => {
    render(<Game initial={nearWin('computer')} rng={() => 0.5} />)
    frame(0)
    frame(16)
    expect(screen.getByText('Computer wins!')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Restart' })).toBeInTheDocument()
  })
})
