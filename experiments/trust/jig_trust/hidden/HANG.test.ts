import { describe, expect, it } from 'vitest';
import * as L from '../logic';

const guessAll = (g: L.Game, letters: string) => [...letters].reduce((x, c) => L.guess(x, c), g);

describe('HANG', () => {
  it('H1 newGame lower-cases the word, with no guesses and 6 misses allowed by default', () => {
    const g = L.newGame('Planet');
    expect(g.word).toBe('planet');
    expect(g.guessed).toEqual([]);
    expect(g.maxMisses).toBe(6);
    expect(L.newGame('x', 3).maxMisses).toBe(3);
    expect(L.status(g)).toBe('playing');
  });
  it('H2 masked shows guessed letters and underscores separated by spaces', () => {
    const g = L.newGame('cat');
    expect(L.masked(g)).toBe('_ _ _');
    expect(L.masked(L.guess(g, 'a'))).toBe('_ a _');
  });
  it('H3 guesses are case-insensitive and fill every occurrence', () => {
    const g = L.guess(L.newGame('banana'), 'A');
    expect(g.guessed).toEqual(['a']);
    expect(L.masked(g)).toBe('_ a _ a _ a');
  });
  it('H4 repeated or invalid guesses return the same game object, and old games are unchanged', () => {
    const g0 = L.newGame('cat');
    const g1 = L.guess(g0, 'a');
    expect(g0.guessed).toEqual([]);
    expect(L.guess(g1, 'a')).toBe(g1);
    expect(L.guess(g1, 'A')).toBe(g1);
    expect(L.guess(g1, 'ab')).toBe(g1);
    expect(L.guess(g1, '1')).toBe(g1);
    expect(L.guess(g1, '')).toBe(g1);
  });
  it('H5 misses count wrong letters and the game is lost at maxMisses', () => {
    const g = guessAll(L.newGame('cat', 3), 'xyz');
    expect(L.misses(g)).toBe(3);
    expect(L.status(g)).toBe('lost');
    expect(L.guess(g, 'c')).toBe(g);
  });
  it('H6 the game is won when every letter is found', () => {
    const g = guessAll(L.newGame('noon'), 'qno');
    expect(L.misses(g)).toBe(1);
    expect(L.status(g)).toBe('won');
    expect(L.masked(g)).toBe('n o o n');
  });
});
