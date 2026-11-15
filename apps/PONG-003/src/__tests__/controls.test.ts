import { describe, expect, it } from 'vitest';
import { pressSpace, restart, start, togglePause } from '../game/controls';
import { createInitialState } from '../game/state';

describe('R-09 phase controls', () => {
  it('starts in ready', () => {
    expect(createInitialState().phase).toBe('ready');
  });
  it('Space cycles ready -> playing -> paused -> playing', () => {
    let s = createInitialState();
    s = pressSpace(s);
    expect(s.phase).toBe('playing');
    s = pressSpace(s);
    expect(s.phase).toBe('paused');
    s = pressSpace(s);
    expect(s.phase).toBe('playing');
  });
  it('start only works from ready; togglePause not from ready', () => {
    const s = createInitialState();
    expect(togglePause(s)).toBe(s);
    expect(start({ ...s, phase: 'paused' }).phase).toBe('paused');
  });
  it('Space is ignored in over', () => {
    const s = { ...createInitialState(), phase: 'over' as const };
    expect(pressSpace(s)).toBe(s);
  });
  it('restart returns a fresh ready state', () => {
    const s = restart(() => 0.5);
    expect(s.phase).toBe('ready');
    expect(s.scores).toEqual({ player: 0, computer: 0 });
    expect(s.winner).toBeNull();
  });
});
