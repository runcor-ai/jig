import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { createBoard } from './game/board';
import { newGame } from './game/game';
import type { GameState } from './game/game';
import { gravityMs } from './game/scoring';

const rng = () => 0.3; // T

const activeCells = () =>
  Array.from(document.querySelectorAll('[data-state="active"]')).map((e) => [
    Number(e.getAttribute('data-col')),
    Number(e.getAttribute('data-row')),
  ]);
const minRow = () => Math.min(...activeCells().map(([, r]) => r));
const minCol = () => Math.min(...activeCells().map(([c]) => c));

afterEach(() => vi.useRealTimers());

describe('App', () => {
  it('renders empty 10x20 board, HUD and next preview (R-01, R-09)', () => {
    render(<App rng={rng} />);
    expect(document.querySelectorAll('[data-testid^="cell-"]')).toHaveLength(200);
    expect(document.querySelectorAll('[data-state="locked"]')).toHaveLength(0);
    expect(screen.getByText('Score')).toBeInTheDocument();
    expect(screen.getByText('Level')).toBeInTheDocument();
    expect(screen.getByText('Rows')).toBeInTheDocument();
    expect(screen.getByTestId('score')).toHaveTextContent('0');
    expect(screen.getByTestId('level')).toHaveTextContent('1');
    expect(screen.getByTestId('next')).toHaveAttribute('data-kind', 'T');
    expect(document.querySelectorAll('[data-testid="next"] [data-filled="true"]')).toHaveLength(4);
  });

  it('keys change the view and call preventDefault (R-12)', () => {
    render(<App rng={rng} />);
    const c0 = minCol();
    expect(fireEvent.keyDown(window, { key: 'ArrowLeft' })).toBe(false);
    expect(minCol()).toBe(c0 - 1);
    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(minCol()).toBe(c0);
    const r0 = minRow();
    expect(fireEvent.keyDown(window, { key: 'ArrowDown' })).toBe(false);
    expect(minRow()).toBe(r0 + 1);
    expect(fireEvent.keyDown(window, { key: 'ArrowUp' })).toBe(false);
    expect(fireEvent.keyDown(window, { key: ' ', code: 'Space' })).toBe(false);
    expect(document.querySelectorAll('[data-state="locked"]')).toHaveLength(4);
    expect(fireEvent.keyDown(window, { key: 'p' })).toBe(false);
    expect(screen.getByText('Paused')).toBeInTheDocument();
    expect(fireEvent.keyDown(window, { key: 'x' })).toBe(true);
  });

  it('gravity moves the piece, not while paused (R-05, R-11)', () => {
    vi.useFakeTimers();
    render(<App rng={rng} />);
    const r0 = minRow();
    act(() => {
      vi.advanceTimersByTime(gravityMs(1));
    });
    expect(minRow()).toBe(r0 + 1);
    fireEvent.keyDown(window, { key: 'P' });
    act(() => {
      vi.advanceTimersByTime(gravityMs(1) * 3);
    });
    expect(minRow()).toBe(r0 + 1);
    fireEvent.keyDown(window, { key: 'ArrowDown' });
    expect(minRow()).toBe(r0 + 1);
    fireEvent.keyDown(window, { key: 'p' });
    act(() => {
      vi.advanceTimersByTime(gravityMs(1));
    });
    expect(minRow()).toBe(r0 + 2);
  });

  it('shows a ghost at the hard-drop row (R-13)', () => {
    render(<App rng={rng} />);
    const ghosts = Array.from(document.querySelectorAll('[data-state="ghost"]'));
    expect(ghosts.length).toBeGreaterThan(0);
    expect(Math.max(...ghosts.map((g) => Number(g.getAttribute('data-row'))))).toBe(19);
  });

  it('game over overlay shows score; Restart resets (R-10)', () => {
    const board = createBoard();
    const over: GameState = { ...newGame(rng), board, score: 1234, rows: 12, level: 2, status: 'over' };
    render(<App rng={rng} initialState={over} />);
    expect(screen.getByText('Game over')).toBeInTheDocument();
    expect(screen.getByTestId('final-score')).toHaveTextContent('1234');
    const c = minCol();
    fireEvent.keyDown(window, { key: 'ArrowLeft' });
    expect(minCol()).toBe(c);
    fireEvent.click(screen.getByRole('button', { name: 'Restart' }));
    expect(screen.queryByText('Game over')).not.toBeInTheDocument();
    expect(screen.getByTestId('score')).toHaveTextContent('0');
    expect(screen.getByTestId('level')).toHaveTextContent('1');
    expect(screen.getByTestId('rows')).toHaveTextContent('0');
  });

  it('HUD updates after a line clear (R-09)', () => {
    const board = createBoard();
    board[19] = Array(10).fill('J').map((c, i) => (i < 4 ? null : c));
    const s: GameState = { ...newGame(rng), board, active: { kind: 'I', rotation: 0, x: 0, y: 0 } };
    render(<App rng={rng} initialState={s} />);
    fireEvent.keyDown(window, { key: ' ' });
    expect(screen.getByTestId('score')).toHaveTextContent('100');
    expect(screen.getByTestId('rows')).toHaveTextContent('1');
  });

  it('removes the key listener on unmount (R-12)', () => {
    const add = vi.spyOn(window, 'addEventListener');
    const remove = vi.spyOn(window, 'removeEventListener');
    const { unmount } = render(<App rng={rng} />);
    const added = add.mock.calls.filter(([t]) => t === 'keydown');
    expect(added.length).toBeGreaterThan(0);
    unmount();
    const removed = remove.mock.calls.filter(([t]) => t === 'keydown');
    for (const [, fn] of added) expect(removed.some(([, f]) => f === fn)).toBe(true);
    add.mockRestore();
    remove.mockRestore();
  });
});
