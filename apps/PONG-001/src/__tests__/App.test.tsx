import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import App from '../App';
import { createInitialState } from '../game/logic';

const scores = () => [screen.getByTestId('player-score').textContent, screen.getByTestId('ai-score').textContent];

describe('App', () => {
  it('renders initial state', () => {
    render(<App />);
    expect(screen.getByTestId('playfield')).toBeTruthy();
    expect(scores()).toEqual(['0', '0']);
    expect(screen.getByRole('button', { name: 'Restart' })).toBeTruthy();
    expect(screen.getByText(/Press Space to start/)).toBeTruthy();
    expect(screen.getByText(/First to 10 points/)).toBeTruthy();
    expect(screen.getByText(/ArrowUp/)).toBeTruthy();
  });
  it('space starts and pauses; unknown keys ignored', () => {
    render(<App />);
    fireEvent.keyDown(window, { key: 'x' });
    expect(screen.getByText(/Press Space to start/)).toBeTruthy();
    fireEvent.keyDown(window, { key: ' ' });
    expect(screen.queryByText(/Press Space to start/)).toBeNull();
    fireEvent.keyDown(window, { key: ' ' });
    expect(screen.getByText(/Paused/)).toBeTruthy();
    fireEvent.keyDown(window, { key: ' ' });
    expect(screen.queryByText(/Paused/)).toBeNull();
  });
  it('prevents default on game keys only', () => {
    render(<App />);
    expect(fireEvent.keyDown(window, { key: 'ArrowDown' })).toBe(false);
    expect(fireEvent.keyDown(window, { key: 'q' })).toBe(true);
  });
  it('shows winner and Restart clears it', () => {
    render(<App initialState={{ ...createInitialState(), status: 'over', winner: 'computer', aiScore: 10, playerScore: 4 }} />);
    expect(screen.getByText('Computer wins!')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Restart' }));
    expect(screen.queryByText('Computer wins!')).toBeNull();
    expect(scores()).toEqual(['0', '0']);
  });
  it('restart mid-game resets scores', () => {
    render(<App initialState={{ ...createInitialState(), status: 'playing', playerScore: 3, aiScore: 2 }} />);
    fireEvent.click(screen.getByRole('button', { name: 'Restart' }));
    expect(scores()).toEqual(['0', '0']);
  });
  it('unmounts cleanly and removes listeners', () => {
    const { unmount } = render(<App />);
    unmount();
    expect(() => fireEvent.keyDown(window, { key: ' ' })).not.toThrow();
  });
});
