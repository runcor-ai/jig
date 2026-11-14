import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

// With this rng the first food lands at (12,10), and each next food one cell further right.
// Call n sees (397 - n) free cells; index 209 is the cell just right of the snake head.
const eatRight = () => { let n = 0; return () => (209.5 / (397 - n++)) }

const head = () => {
  const el = document.querySelector('[data-cell="head"]')!
  return { x: Number(el.getAttribute('data-x')), y: Number(el.getAttribute('data-y')) }
}
const tick = (ms: number) => act(() => { vi.advanceTimersByTime(ms) })
const key = (k: string) => act(() => { fireEvent.keyDown(window, { key: k }) })
const setRandom = (v: number) => vi.spyOn(Math, 'random').mockReturnValue(v)

beforeEach(() => { vi.useFakeTimers(); setRandom(0) })
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks() })

describe('App', () => {
  it('R-07/R-09 shows scores and a 400-cell board', () => {
    render(<App />)
    expect(screen.getByText(/Score:/)).toBeTruthy()
    expect(screen.getByText(/Best:/)).toBeTruthy()
    expect(document.querySelectorAll('[data-cell]')).toHaveLength(400)
    expect(document.querySelectorAll('[data-cell="food"]')).toHaveLength(1)
    expect(document.querySelectorAll('[data-cell="head"]')).toHaveLength(1)
    expect(document.querySelectorAll('[data-cell="body"]')).toHaveLength(2)
  })

  it('R-03 keys steer (arrows and WASD) and are default-prevented', () => {
    render(<App />)
    const ev = new KeyboardEvent('keydown', { key: 'ArrowDown', cancelable: true })
    act(() => { window.dispatchEvent(ev) })
    expect(ev.defaultPrevented).toBe(true)
    tick(150)
    expect(head()).toEqual({ x: 11, y: 11 })
    key('a'); tick(150)
    expect(head()).toEqual({ x: 10, y: 11 })
    key('W'); tick(150)
    expect(head()).toEqual({ x: 10, y: 10 })
    key('ArrowRight'); tick(150)
    expect(head()).toEqual({ x: 11, y: 10 })
  })

  it('R-03 reverse request is ignored', () => {
    render(<App />)
    key('ArrowLeft'); tick(150)
    expect(head()).toEqual({ x: 12, y: 10 })
  })

  it('R-08 space pauses and resumes', () => {
    render(<App />)
    const ev = new KeyboardEvent('keydown', { key: ' ', cancelable: true })
    act(() => { window.dispatchEvent(ev) })
    expect(ev.defaultPrevented).toBe(true)
    expect(screen.getByText('Paused')).toBeTruthy()
    tick(1000)
    expect(head()).toEqual({ x: 11, y: 10 })
    key(' ')
    expect(screen.queryByText('Paused')).toBeNull()
    tick(150)
    expect(head()).toEqual({ x: 12, y: 10 })
  })

  it('R-06/R-07 game over, final score, restart keeps best', () => {
    vi.spyOn(Math, 'random').mockImplementation(eatRight())
    render(<App />)
    tick(5000)
    expect(screen.getByText('Game over')).toBeTruthy()
    expect(screen.getByTestId('final-score').textContent).toBe('80')
    expect(screen.getByTestId('best').textContent).toBe('80')
    key(' ') // ignored when over
    expect(screen.queryByText('Paused')).toBeNull()
    fireEvent.click(screen.getByText('Restart'))
    expect(screen.getByTestId('score').textContent).toBe('0')
    expect(screen.getByTestId('best').textContent).toBe('80')
    expect(screen.queryByText('Game over')).toBeNull()
  })

  it('R-06 wall hit with score 0 shows game over and Restart', () => {
    render(<App />)
    tick(150 * 10)
    expect(screen.getByText('Game over')).toBeTruthy()
    expect(screen.getByText('Restart')).toBeTruthy()
  })

  it('R-05 speed increases after the 5th food', () => {
    vi.spyOn(Math, 'random').mockImplementation(eatRight())
    render(<App />)
    tick(150 * 5)
    expect(screen.getByTestId('score').textContent).toBe('50')
    tick(135)
    expect(head().x).toBe(17)
  })

  it('R-10 unmount stops timers without errors', () => {
    const { unmount } = render(<App />)
    unmount()
    expect(() => tick(5000)).not.toThrow()
    expect(vi.getTimerCount()).toBe(0)
  })
})
