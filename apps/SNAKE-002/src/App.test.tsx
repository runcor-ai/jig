import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

// The timer is re-armed after each render, so advance in small steps, each in its own act().
const tick = (ms: number) => {
  for (let t = 0; t < ms; t += 150) act(() => { vi.advanceTimersByTime(Math.min(150, ms - t)) })
}
const key = (k: string) => act(() => { fireEvent.keyDown(window, { key: k }) })
const head = (c: HTMLElement) => c.querySelector('.snake-head')!
const idx = (c: HTMLElement, el: Element) => Array.from(c.querySelectorAll('.cell')).indexOf(el)

beforeEach(() => { vi.useFakeTimers() })
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.useRealTimers() })

describe('rendering (R-11)', () => {
  it('draws 400 cells, one food, 3 snake cells, one head', () => {
    const { container } = render(<App />)
    expect(container.querySelectorAll('.cell')).toHaveLength(400)
    expect(container.querySelectorAll('.food')).toHaveLength(1)
    expect(container.querySelectorAll('.snake')).toHaveLength(3)
    expect(container.querySelectorAll('.snake-head')).toHaveLength(1)
    expect(screen.getAllByTestId('food')).toHaveLength(1)
  })
})

describe('score panel (R-09)', () => {
  it('shows Score and Best', () => {
    render(<App />)
    expect(screen.getByText('Score: 0')).toBeInTheDocument()
    expect(screen.getByText('Best: 0')).toBeInTheDocument()
  })
})

describe('pause (R-10)', () => {
  it('pauses, ignores ticks and directions, resumes', () => {
    vi.spyOn(Math, 'random').mockReturnValue(0)
    const { container } = render(<App />)
    const start = idx(container, head(container))
    key(' ')
    expect(screen.getByText('Paused')).toBeInTheDocument()
    key('ArrowUp')
    tick(1000)
    expect(idx(container, head(container))).toBe(start)
    key(' ')
    expect(screen.queryByText('Paused')).toBeNull()
    tick(150)
    expect(idx(container, head(container))).toBe(start + 1)
  })
})

describe('movement and direction (R-02, R-03)', () => {
  it('moves right then turns up', () => {
    vi.spyOn(Math, 'random').mockReturnValue(0)
    const { container } = render(<App />)
    const start = idx(container, head(container))
    tick(150)
    expect(idx(container, head(container))).toBe(start + 1)
    key('ArrowUp')
    tick(150)
    expect(idx(container, head(container))).toBe(start + 1 - 20)
  })
  it('preventDefault on arrow keys', () => {
    render(<App />)
    const ev = new KeyboardEvent('keydown', { key: 'ArrowDown', cancelable: true })
    act(() => { window.dispatchEvent(ev) })
    expect(ev.defaultPrevented).toBe(true)
  })
})

describe('game over and restart (R-07, R-08, R-09)', () => {
  it('ends at the wall and restarts', () => {
    vi.spyOn(Math, 'random').mockReturnValue(0) // food at (0,0), out of the way
    const { container } = render(<App />)
    tick(150 * 15)
    expect(screen.getByText('Game over')).toBeInTheDocument()
    expect(screen.getByText('Final score: 0')).toBeInTheDocument()
    const btn = screen.getByRole('button', { name: 'Restart' })
    const frozen = idx(container, head(container))
    tick(2000)
    expect(idx(container, head(container))).toBe(frozen)
    fireEvent.click(btn)
    expect(screen.queryByText('Game over')).toBeNull()
    expect(container.querySelectorAll('.snake')).toHaveLength(3)
    expect(idx(container, head(container))).toBe(10 * 20 + 10)
    expect(screen.getByText('Best: 0')).toBeInTheDocument()
  })
  it('keeps best after restart when food was eaten', () => {
    // rng 0 puts food on the first free cell (0,0): go up, then left to eat it
    vi.spyOn(Math, 'random').mockReturnValue(0)
    render(<App />)
    key('ArrowUp')
    tick(150 * 10) // y: 10 -> 0
    key('ArrowLeft')
    tick(150 * 10) // x: 10 -> 0, eats food at (0,0)
    expect(screen.getByText('Score: 10')).toBeInTheDocument()
    expect(screen.getByText('Best: 10')).toBeInTheDocument()
    tick(5000) // hits wall
    expect(screen.getByText('Final score: 10')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Restart' }))
    expect(screen.getByText('Score: 0')).toBeInTheDocument()
    expect(screen.getByText('Best: 10')).toBeInTheDocument()
  })
})
