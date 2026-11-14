import { describe, expect, it } from 'vitest';
import * as L from '../logic';

describe('MASTER', () => {
  it('H1 an exact match is all black, and no common colour is zero', () => {
    expect(L.score(['r', 'g', 'b', 'y'], ['r', 'g', 'b', 'y'])).toEqual({ black: 4, white: 0 });
    expect(L.score(['r', 'r', 'r', 'r'], ['g', 'g', 'b', 'b'])).toEqual({ black: 0, white: 0 });
  });
  it('H2 right colours in the wrong places are white', () => {
    expect(L.score(['r', 'g', 'b', 'y'], ['y', 'b', 'g', 'r'])).toEqual({ black: 0, white: 4 });
    expect(L.score(['r', 'g', 'b', 'y'], ['r', 'b', 'o', 'p'])).toEqual({ black: 1, white: 1 });
  });
  it('H3 repeated colours are matched at most once', () => {
    expect(L.score(['r', 'r', 'g', 'b'], ['r', 'g', 'r', 'r'])).toEqual({ black: 1, white: 2 });
    expect(L.score(['r', 'g', 'g', 'g'], ['g', 'r', 'r', 'r'])).toEqual({ black: 0, white: 2 });
    expect(L.score(['r', 'g', 'b', 'y'], ['r', 'r', 'r', 'r'])).toEqual({ black: 1, white: 0 });
  });
  it('H4 newGame and guess record guesses without changing the old game', () => {
    const g0 = L.newGame(['r', 'g', 'b', 'y']);
    expect(g0.maxTurns).toBe(10);
    expect(g0.guesses).toEqual([]);
    const g1 = L.guess(g0, ['r', 'r', 'r', 'r']);
    expect(g1.guesses).toEqual([['r', 'r', 'r', 'r']]);
    expect(g0.guesses).toEqual([]);
    expect(L.status(g1)).toBe('playing');
  });
  it('H5 a guess of the wrong length returns the same game object', () => {
    const g = L.newGame(['r', 'g', 'b', 'y']);
    expect(L.guess(g, ['r', 'g', 'b'])).toBe(g);
  });
  it('H6 winning and losing end the game', () => {
    const won = L.guess(L.newGame(['r', 'g', 'b', 'y']), ['r', 'g', 'b', 'y']);
    expect(L.status(won)).toBe('won');
    expect(L.guess(won, ['r', 'r', 'r', 'r'])).toBe(won);
    let g = L.newGame(['r', 'g', 'b', 'y'], 2);
    g = L.guess(L.guess(g, ['o', 'o', 'o', 'o']), ['p', 'p', 'p', 'p']);
    expect(L.status(g)).toBe('lost');
    expect(L.guess(g, ['r', 'g', 'b', 'y'])).toBe(g);
  });
});
