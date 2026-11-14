import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { createBoard } from './game/board';
import { createInitialState } from './game/game';

const BAR_RNG = () => 0.5 / 7;

const active = (c: HTMLElement) => Array.from(c.querySelectorAll('[data-active="true"]'));
const rowsOf = (c: HTMLElement) => active(c).map((e) => Number(e.getAttribute('data-row')));
const colsOf = (c: HTMLElement) => active(c).map((e) => Number(e.getAttribute('data-col')));
const key = (k: string, extra: KeyboardEventInit = {}) => fireEvent.keyDown(window, { key: k, ...extra });
const advance = (ms: number) => act(() => void vi.advanceTimersByTime(ms));

beforeEach(() => void vi.useFakeTimers());
afterEach(() => void vi.useRealTimers());

describe('R-11 rendering and HUD', () => {
  it('renders 200 cells, active piece, HUD and 4-cell preview', () => {
    const { container } = render(<App random={BAR_RNG} />);
    expect(screen.getAllByTestId('cell')).toHaveLength(200);
    expect(active(container)).toHaveLength(4);
    expect(container.querySelectorAll('[data-testid="preview-cell"][data-filled="true"]')).toHaveLength(4);
    expect(screen.getByText('Score')).toBeInTheDocument();
    expect(screen.getByText('Level')).toBeInTheDocument();
    expect(screen.getByText('Rows')).toBeInTheDocument();
    expect(screen.getByTestId('score')).toHaveTextContent('0');
    expect(screen.getByTestId('level')).toHaveTextContent('1');
  });

  it('marks ghost cells distinctly', () => {
    const { container } = render(<App random={BAR_RNG} />);
    expect(container.querySelectorAll('[data-ghost="true"]')).toHaveLength(4);
  });
});

describe('R-13 legend', () => {
  it('lists the controls', () => {
    render(<App random={BAR_RNG} />);
    for (const t of ['Left', 'Right', 'Up', 'Down', 'Space', 'P']) {
      expect(screen.getByText(t, { selector: 'kbd' })).toBeInTheDocument();
    }
    expect(screen.getByText(/hard drop/)).toBeInTheDocument();
  });
});

describe('R-10 keyboard', () => {
  it('maps keys to actions and prevents default for arrows and Space', () => {
    const { container } = render(<App random={BAR_RNG} />);
    const col0 = Math.min(...colsOf(container));
    expect(key('ArrowLeft')).toBe(false);
    expect(Math.min(...colsOf(container))).toBe(col0 - 1);
    expect(key('ArrowRight')).toBe(false);
    expect(Math.min(...colsOf(container))).toBe(col0);
    expect(key('ArrowDown')).toBe(false);
    expect(new Set(rowsOf(container))).toEqual(new Set([2]));
    expect(key('ArrowUp')).toBe(false);
    expect(new Set(colsOf(container)).size).toBe(1); // vertical bar
    expect(key(' ')).toBe(false);
    expect(container.querySelectorAll('[data-testid="cell"][data-filled="true"]')).toHaveLength(8);
  });

  it('ignores auto-repeat for Space and Up but not Left/Right/Down', () => {
    const { container } = render(<App random={BAR_RNG} />);
    key(' ', { repeat: true });
    expect(container.querySelectorAll('[data-testid="cell"][data-filled="true"]')).toHaveLength(4);
    key('ArrowUp', { repeat: true });
    expect(new Set(rowsOf(container))).toEqual(new Set([1]));
    key('ArrowDown', { repeat: true });
    expect(new Set(rowsOf(container))).toEqual(new Set([2]));
    const c = Math.min(...colsOf(container));
    key('ArrowLeft', { repeat: true });
    expect(Math.min(...colsOf(container))).toBe(c - 1);
  });

  it('removes the listener on unmount', () => {
    const spy = vi.spyOn(window, 'removeEventListener');
    const { unmount } = render(<App random={BAR_RNG} />);
    unmount();
    expect(spy.mock.calls.some(([t]) => t === 'keydown')).toBe(true);
    expect(() => key('ArrowLeft')).not.toThrow();
  });
});

describe('R-04 / R-07 timer', () => {
  it('moves down one row per interval', () => {
    const { container } = render(<App random={BAR_RNG} />);
    advance(999);
    expect(new Set(rowsOf(container))).toEqual(new Set([1]));
    advance(1);
    expect(new Set(rowsOf(container))).toEqual(new Set([2]));
  });

  it('re-creates the timer with the faster interval after a level-up', () => {
    const board = createBoard();
    for (let c = 4; c < 10; c++) board[19][c] = 'tee';
    const base = createInitialState(BAR_RNG);
    const initial = { ...base, board, rows: 9, active: { ...base.active, x: 0, y: 0 } };
    const { container } = render(<App random={BAR_RNG} initialState={initial} />);
    key(' ');
    expect(screen.getByTestId('level')).toHaveTextContent('2');
    expect(screen.getByTestId('rows')).toHaveTextContent('10');
    expect(screen.getByTestId('score')).toHaveTextContent('100');
    advance(919);
    expect(new Set(rowsOf(container))).toEqual(new Set([1]));
    advance(1);
    expect(new Set(rowsOf(container))).toEqual(new Set([2]));
  });
});

describe('R-09 pause', () => {
  it('shows Paused, freezes input and timers, and resumes', () => {
    const { container } = render(<App random={BAR_RNG} />);
    key('p');
    expect(screen.getByText('Paused')).toBeInTheDocument();
    advance(5000);
    key('ArrowLeft');
    key('ArrowDown');
    key(' ');
    expect(new Set(rowsOf(container))).toEqual(new Set([1]));
    key('P');
    expect(screen.queryByText('Paused')).not.toBeInTheDocument();
    advance(1000);
    expect(new Set(rowsOf(container))).toEqual(new Set([2]));
  });
});

describe('R-08 game over', () => {
  it('shows final score and Restart, which resets the game', () => {
    const base = createInitialState(BAR_RNG);
    const board = createBoard();
    for (const y of [0, 1]) for (let c = 0; c < 9; c++) board[y][c] = 'tee';
    render(<App random={BAR_RNG} initialState={{ ...base, board, score: 700, rows: 4 }} />);
    key(' '); // lock into blocked spawn -> over
    expect(screen.getByText(/Final score: 700/)).toBeInTheDocument();
    advance(3000);
    key('ArrowLeft');
    expect(screen.getByText(/Final score: 700/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Restart' }));
    expect(screen.queryByText(/Final score/)).not.toBeInTheDocument();
    expect(screen.getByTestId('score')).toHaveTextContent('0');
    expect(screen.getByTestId('level')).toHaveTextContent('1');
    expect(screen.getByTestId('rows')).toHaveTextContent('0');
  });
});
