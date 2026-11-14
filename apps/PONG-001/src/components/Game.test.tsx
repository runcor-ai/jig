import { act, cleanup, fireEvent, render, renderHook, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Game } from './Game';
import { createInitialState } from '../game/state';
import { useGameLoop } from '../hooks/useGameLoop';
import { FIELD_HEIGHT, FIELD_WIDTH, MAX_DT } from '../game/constants';

let callbacks = new Map<number, FrameRequestCallback>();
let nextId = 1;
let now = 0;

function frame(ms: number) {
  now += ms;
  const pending = [...callbacks.entries()];
  callbacks = new Map();
  act(() => {
    for (const [, cb] of pending) cb(now);
  });
}

beforeEach(() => {
  callbacks = new Map();
  nextId = 1;
  now = 1000;
  vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
    const id = nextId++;
    callbacks.set(id, cb);
    return id;
  });
  vi.stubGlobal('cancelAnimationFrame', (id: number) => {
    callbacks.delete(id);
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const space = () => fireEvent.keyDown(window, { key: ' ', code: 'Space' });

describe('Game UI', () => {
  it('shows start prompt, 0-0 and a fixed 800x500 field', () => {
    render(<Game />);
    expect(screen.getByText('Press Space to start')).toBeInTheDocument();
    expect(screen.getByTestId('player-score')).toHaveTextContent('0');
    expect(screen.getByTestId('computer-score')).toHaveTextContent('0');
    const field = screen.getByTestId('playfield');
    expect(field).toHaveStyle({ width: `${FIELD_WIDTH}px`, height: `${FIELD_HEIGHT}px` });
    expect(screen.getByTestId('ball')).toHaveAttribute('data-x');
    expect(screen.getByTestId('left-paddle').style.transform).toContain('translate(0px');
  });

  it('Space starts, pauses and resumes', () => {
    render(<Game />);
    space();
    expect(screen.queryByText('Press Space to start')).not.toBeInTheDocument();
    space();
    expect(screen.getByText('Paused')).toBeInTheDocument();
    space();
    expect(screen.queryByText('Paused')).not.toBeInTheDocument();
  });

  it('key repeat toggles only once', () => {
    render(<Game />);
    space();
    fireEvent.keyDown(window, { key: ' ', code: 'Space', repeat: true });
    fireEvent.keyDown(window, { key: ' ', code: 'Space', repeat: true });
    expect(screen.queryByText('Paused')).not.toBeInTheDocument();
  });

  it('arrow keys call preventDefault', () => {
    render(<Game />);
    const notPrevented = fireEvent.keyDown(window, { key: 'ArrowUp' });
    expect(notPrevented).toBe(false);
  });

  it('moves the ball while playing and the paddle with keys', () => {
    render(<Game />);
    space();
    const ballBefore = screen.getByTestId('ball').getAttribute('data-x');
    const padBefore = Number(screen.getByTestId('left-paddle').getAttribute('data-y'));
    fireEvent.keyDown(window, { key: 'w' });
    frame(16);
    frame(16);
    expect(screen.getByTestId('ball').getAttribute('data-x')).not.toBe(ballBefore);
    expect(Number(screen.getByTestId('left-paddle').getAttribute('data-y'))).toBeLessThan(padBefore);
  });

  const nearWin = () => ({
    ...createInitialState(),
    playerScore: 9,
    ai: { y: 300, targetY: 345, timer: 0 },
    ball: { x: 799, y: 10, vx: 360, vy: 0 },
  });

  it('shows winner and Restart, which resets; Space does not restart', () => {
    render(<Game initialState={nearWin()} />);
    space();
    frame(16);
    frame(16);
    expect(screen.getByText('You win!')).toBeInTheDocument();
    expect(screen.getByTestId('player-score')).toHaveTextContent('10');
    space();
    expect(screen.getByText('You win!')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Restart' }));
    expect(screen.getByText('Press Space to start')).toBeInTheDocument();
    expect(screen.getByTestId('player-score')).toHaveTextContent('0');
    expect(screen.getByTestId('computer-score')).toHaveTextContent('0');
  });

  it('shows Computer wins when the computer reaches 10', () => {
    const s = {
      ...createInitialState(),
      computerScore: 9,
      player: { y: 300 },
      ball: { x: -8, y: 10, vx: -360, vy: 0 },
    };
    render(<Game initialState={s} />);
    space();
    frame(16);
    frame(16);
    frame(16);
    expect(screen.getByText('Computer wins')).toBeInTheDocument();
  });
});

describe('useGameLoop (R-10)', () => {
  it('clamps dt and cancels on unmount', () => {
    const dts: number[] = [];
    const { unmount } = renderHook(() => useGameLoop((dt) => dts.push(dt), true));
    frame(0); // first frame sets baseline
    frame(5000); // tab switch
    frame(10);
    expect(dts[0]).toBeCloseTo(MAX_DT);
    expect(dts[1]).toBeCloseTo(0.01);
    expect(Math.max(...dts)).toBeLessThanOrEqual(MAX_DT);
    unmount();
    expect(callbacks.size).toBe(0);
  });

  it('does not run when inactive', () => {
    const cb = vi.fn();
    renderHook(() => useGameLoop(cb, false));
    frame(16);
    frame(16);
    expect(cb).not.toHaveBeenCalled();
  });
});
