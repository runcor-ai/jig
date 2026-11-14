import { describe, expect, it } from 'vitest';
import * as L from '../logic';

const ALLOWED = ['apple', 'paper', 'crane', 'pupil', 'lemon', 'spool', 'allee', 'eagle'];

describe('WORDS', () => {
  it('H1 an exact guess is all right, and no shared letters is all absent', () => {
    expect(L.mark('crane', 'crane')).toEqual(['right', 'right', 'right', 'right', 'right']);
    expect(L.mark('crane', 'spool')).toEqual(['absent', 'absent', 'absent', 'absent', 'absent']);
  });
  it('H2 letters in the wrong place are present', () => {
    expect(L.mark('apple', 'paper')).toEqual(['present', 'present', 'right', 'present', 'absent']);
  });
  it('H3 each answer letter is used at most once', () => {
    expect(L.mark('lemon', 'allee')).toEqual(['absent', 'present', 'absent', 'present', 'absent']);
    expect(L.mark('apple', 'pupil')).toEqual(['present', 'absent', 'right', 'absent', 'present']);
  });
  it('H4 guess adds allowed words, lower-cased, and keeps the old game', () => {
    const g0 = L.newGame('apple');
    expect(g0.maxGuesses).toBe(6);
    const g1 = L.guess(g0, 'PAPER', ALLOWED);
    expect(g1.guesses).toEqual(['paper']);
    expect(g0.guesses).toEqual([]);
    expect(L.guess(g1, 'zzzzz', ALLOWED)).toBe(g1);
    expect(L.guess(g1, 'pap', ALLOWED)).toBe(g1);
  });
  it('H5 winning and losing end the game', () => {
    const won = L.guess(L.newGame('apple'), 'apple', ALLOWED);
    expect(L.status(won)).toBe('won');
    expect(L.guess(won, 'paper', ALLOWED)).toBe(won);
    let g = L.newGame('apple', 2);
    g = L.guess(L.guess(g, 'crane', ALLOWED), 'lemon', ALLOWED);
    expect(L.status(g)).toBe('lost');
  });
  it('H6 the keyboard keeps the best mark of each letter', () => {
    let g = L.newGame('apple');
    g = L.guess(g, 'paper', ALLOWED);
    expect(L.keyboard(g)).toEqual({ p: 'right', a: 'present', e: 'present', r: 'absent' });
    g = L.guess(g, 'eagle', ALLOWED);
    expect(L.keyboard(g).e).toBe('right');
    expect(L.keyboard(g).g).toBe('absent');
  });
});
