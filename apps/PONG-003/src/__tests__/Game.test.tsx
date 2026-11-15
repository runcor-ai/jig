import { act, fireEvent, render, renderHook, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { Game } from '../components/Game';
import { createInitialState, type GameState } from '../game/state';
import { useGameLoop } from '../hooks/useGameLoop';

const rng = () => 0.5;
const space = (extra: KeyboardEventInit = {}) => fireEvent.keyDown(window, { key: ' ', code: 'Space', ...extra });
const field = () => screen.getByTestId('playfield');

/** Stub rAF so tests can run frames by hand. */
function stubRaf() {
  let cb: FrameRequestCallback | null = null;
  let nextId = 1;
  const cancel = vi.fn();
  vi.stubGlobal('requestAnimationFrame', (f: FrameRequestCallback) => {
    cb = f;
    return nextId++;
  });
  vi.stubGlobal('cancelAnimationFrame', cancel);
  return {
    cancel,
    lastId: () => nextId - 1,
    frame: (t: number) => act(() => cb!(t)),
  };
}

afterEach(() => vi.unstubAllGlobals());

describe('R-01 / R-10 rendering', () => {
  it('renders a fixed 800x500 playfield, scores and start message', () => {
    render(<Game rng={rng} />);
    expect(field().style.width).toBe('800px');
    expect(field().style.height).toBe('500px');
    expect(screen.getByTestId('score-player').textContent).toBe('0');
    expect(screen.getByTestId('score-computer').textContent).toBe('0');
    expect(screen.getByText('Press Space to start')).toBeTruthy();
    expect(screen.queryByText('Restart')).toBeNull();
    expect(screen.queryByText('You win!')).toBeNull();
  });

  it('shows the winner and Restart only in over; Restart resets', () => {
    const over: GameState = {
      ...createInitialState(rng),
      phase: 'over',
      winner: 'player',
      scores: { player: 10, computer: 7 },
    };
    render(<Game initialState={over} rng={rng} />);
    expect(screen.getByText('You win!')).toBeTruthy();
    expect(screen.getByTestId('score-player').textContent).toBe('10');
    expect(screen.getByTestId('score-computer').textContent).toBe('7');
    fireEvent.click(screen.getByText('Restart'));
    expect(screen.getByTestId('score-player').textContent).toBe('0');
    expect(screen.getByTestId('score-computer').textContent).toBe('0');
    expect(screen.getByText('Press Space to start')).toBeTruthy();
    expect(screen.queryByText('Restart')).toBeNull();
  });

  it('shows "Computer wins" when the computer wins', () => {
    const over: GameState = { ...createInitialState(rng), phase: 'over', winner: 'computer', scores: { player: 3, computer: 10 } };
    render(<Game initialState={over} rng={rng} />);
    expect(screen.getByText('Computer wins')).toBeTruthy();
  });

  it('updates scores as the loop runs', () => {
    const raf = stubRaf();
    const s = createInitialState(rng);
    const state: GameState = {
      ...s,
      phase: 'playing',
      scores: { player: 2, computer: 3 },
      ball: { ...s.ball, x: 799, vx: 300, vy: 0 },
    };
    render(<Game initialState={state} rng={rng} />);
    raf.frame(0);
    raf.frame(16);
    expect(screen.getByTestId('score-player').textContent).toBe('3');
    expect(screen.getByTestId('score-computer').textContent).toBe('3');
  });
});

describe('R-02 keyboard mapping', () => {
  it.each([
    ['w', 'up'],
    ['ArrowUp', 'up'],
    ['s', 'down'],
    ['ArrowDown', 'down'],
  ])('%s -> %s and keyup clears', (key, dir) => {
    render(<Game rng={rng} />);
    expect(field().getAttribute('data-input')).toBe('none');
    fireEvent.keyDown(window, { key });
    expect(field().getAttribute('data-input')).toBe(dir);
    fireEvent.keyUp(window, { key });
    expect(field().getAttribute('data-input')).toBe('none');
  });

  it('up and down together cancel out', () => {
    render(<Game rng={rng} />);
    fireEvent.keyDown(window, { key: 'w' });
    fireEvent.keyDown(window, { key: 's' });
    expect(field().getAttribute('data-input')).toBe('none');
  });
});

describe('R-09 Space handling', () => {
  it('starts, pauses, resumes, and ignores key repeat', () => {
    render(<Game rng={rng} />);
    space();
    expect(screen.queryByText('Press Space to start')).toBeNull();
    expect(screen.queryByText('Paused')).toBeNull();
    space({ repeat: true });
    expect(screen.queryByText('Paused')).toBeNull();
    space();
    expect(screen.getByText('Paused')).toBeTruthy();
    space({ repeat: true });
    expect(screen.getByText('Paused')).toBeTruthy();
    space();
    expect(screen.queryByText('Paused')).toBeNull();
  });

  it('is ignored in over', () => {
    const over: GameState = { ...createInitialState(rng), phase: 'over', winner: 'player' };
    render(<Game initialState={over} rng={rng} />);
    space();
    expect(screen.getByText('You win!')).toBeTruthy();
    expect(screen.queryByText('Paused')).toBeNull();
  });
});

describe('R-11 game loop', () => {
  it('clamps dt to 0.05 s', () => {
    const raf = stubRaf();
    const onFrame = vi.fn();
    renderHook(() => useGameLoop(onFrame));
    raf.frame(0);
    raf.frame(1000);
    expect(onFrame).toHaveBeenLastCalledWith(0.05);
    raf.frame(1010);
    expect(onFrame.mock.lastCall![0]).toBeCloseTo(0.01);
  });

  it('cancels the pending frame on unmount', () => {
    const raf = stubRaf();
    const { unmount } = renderHook(() => useGameLoop(() => {}));
    raf.frame(0);
    const id = raf.lastId();
    unmount();
    expect(raf.cancel).toHaveBeenCalledWith(id);
  });
});
