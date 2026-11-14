import { act, fireEvent, render, renderHook, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../App';
import { BALL_SIZE, DT_CAP_MS, PADDLE_H, WIDTH } from '../game/config';
import { createInitialState } from '../game/logic';
import { useGameLoop } from '../hooks/useGameLoop';

// manual requestAnimationFrame
let queue: Map<number, FrameRequestCallback>;
let nextId: number;
let clock: number;
const cancelSpy = vi.fn();

function frame(advanceMs = 16) {
  clock += advanceMs;
  const cbs = [...queue.values()];
  queue.clear();
  act(() => cbs.forEach((cb) => cb(clock)));
}

beforeEach(() => {
  queue = new Map();
  nextId = 1;
  clock = 1000;
  cancelSpy.mockClear();
  vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
    const id = nextId++;
    queue.set(id, cb);
    return id;
  });
  vi.stubGlobal('cancelAnimationFrame', (id: number) => {
    cancelSpy(id);
    queue.delete(id);
  });
});
afterEach(() => vi.unstubAllGlobals());

const y = (id: string) => {
  const m = /translate\([^,]+px, ([-\d.]+)px\)/.exec(screen.getByTestId(id).style.transform);
  return parseFloat(m![1]);
};
const x = (id: string) => parseFloat(/translate\(([-\d.]+)px/.exec(screen.getByTestId(id).style.transform)![1]);

describe('rendering (R-01, R-09)', () => {
  it('renders playfield, paddles, ball, scores, instructions', () => {
    render(<App />);
    const field = screen.getByTestId('playfield');
    expect(field).toContainElement(screen.getByTestId('paddle-left'));
    expect(field).toContainElement(screen.getByTestId('paddle-right'));
    expect(field).toContainElement(screen.getByTestId('ball'));
    expect(screen.getByTestId('score-player')).toHaveTextContent('0');
    expect(screen.getByTestId('score-computer')).toHaveTextContent('0');
    expect(screen.getByTestId('status')).toHaveTextContent('playing');
    expect(screen.getByText(/W\/S/)).toHaveTextContent(/arrow/i);
  });
  it('ball position changes as frames run (R-01, R-08)', () => {
    render(<App />);
    const x0 = x('ball');
    frame();
    frame();
    expect(x('ball')).not.toBe(x0);
  });
});

describe('keyboard (R-02)', () => {
  it.each([
    ['ArrowUp', -1],
    ['w', -1],
    ['ArrowDown', 1],
    ['s', 1],
  ])('key %s moves paddle direction %i and release stops', (key, sign) => {
    render(<App />);
    frame(); // initial frame sets baseline
    const y0 = y('paddle-left');
    fireEvent.keyDown(window, { key });
    frame();
    const y1 = y('paddle-left');
    expect(Math.sign(y1 - y0)).toBe(sign);
    fireEvent.keyUp(window, { key });
    frame();
    expect(y('paddle-left')).toBe(y1);
  });
  it('removes window listeners on unmount', () => {
    const spy = vi.spyOn(window, 'removeEventListener');
    const { unmount } = render(<App />);
    unmount();
    const removed = spy.mock.calls.map((c) => c[0]);
    expect(removed).toEqual(expect.arrayContaining(['keydown', 'keyup']));
    spy.mockRestore();
  });
});

describe('win and restart (R-06, R-07)', () => {
  const nearWin = () => ({
    ...createInitialState(),
    playerScore: 9,
    rightY: 0,
    ball: { x: WIDTH - 2, y: 400, vx: 300, vy: 0 },
  });

  it('shows winner on reaching 10 and stops updating', () => {
    render(<App initialState={nearWin()} />);
    frame();
    frame();
    expect(screen.getByTestId('score-player')).toHaveTextContent('10');
    expect(screen.getByTestId('winner')).toHaveTextContent('You win!');
    expect(screen.getByTestId('status')).toHaveTextContent('gameover');
    expect(queue.size).toBe(0); // loop stopped
  });
  it('shows computer win message', () => {
    render(
      <App
        initialState={{ ...createInitialState(), computerScore: 9, leftY: 0, ball: { x: -BALL_SIZE, y: 400, vx: -300, vy: 0 } }}
      />,
    );
    frame();
    frame();
    expect(screen.getByTestId('winner')).toHaveTextContent('Computer wins!');
  });
  it('Restart is present in both states and resets the game', () => {
    render(<App initialState={nearWin()} />);
    expect(screen.getByRole('button', { name: /restart/i })).toBeInTheDocument();
    frame();
    frame();
    expect(screen.getByTestId('winner')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /restart/i }));
    expect(screen.queryByTestId('winner')).toBeNull();
    expect(screen.getByTestId('score-player')).toHaveTextContent('0');
    expect(screen.getByTestId('score-computer')).toHaveTextContent('0');
    expect(screen.getByTestId('status')).toHaveTextContent('playing');
    expect(y('paddle-left')).toBe((500 - PADDLE_H) / 2);
    const bx = x('ball');
    frame();
    frame();
    expect(x('ball')).not.toBe(bx);
  });
});

describe('pause (R-10)', () => {
  it('Space toggles pause and freezes state', () => {
    render(<App />);
    frame();
    fireEvent.keyDown(window, { key: ' ', code: 'Space' });
    expect(screen.getByTestId('status')).toHaveTextContent('paused');
    const bx = x('ball');
    frame();
    frame();
    expect(x('ball')).toBe(bx);
    fireEvent.keyDown(window, { key: ' ', code: 'Space' });
    expect(screen.getByTestId('status')).toHaveTextContent('playing');
    frame();
    frame();
    expect(x('ball')).not.toBe(bx);
  });
});

describe('game loop (R-08)', () => {
  it('calls tick once per frame with dt clamped to the cap', () => {
    const tick = vi.fn();
    renderHook(() => useGameLoop(tick, true));
    frame(16); // first frame: dt 0 baseline
    frame(1000); // huge gap
    expect(tick).toHaveBeenCalledTimes(2);
    expect(tick.mock.calls[1][0]).toBeCloseTo(DT_CAP_MS / 1000);
    frame(16);
    expect(tick).toHaveBeenCalledTimes(3);
    expect(tick.mock.calls[2][0]).toBeCloseTo(0.016);
  });
  it('cancels the frame on unmount', () => {
    const tick = vi.fn();
    const { unmount } = renderHook(() => useGameLoop(tick, true));
    unmount();
    expect(cancelSpy).toHaveBeenCalled();
    expect(queue.size).toBe(0);
  });
  it('does not tick when inactive', () => {
    const tick = vi.fn();
    renderHook(() => useGameLoop(tick, false));
    frame();
    expect(tick).not.toHaveBeenCalled();
  });
});
