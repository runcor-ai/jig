import { describe, expect, it } from 'vitest';
import * as L from '../logic';

describe('YAHTZ', () => {
  it('H1 the upper section sums matching dice', () => {
    expect(L.scoreCategory([1, 1, 2, 3, 1], 'ones')).toBe(3);
    expect(L.scoreCategory([6, 6, 2, 3, 6], 'sixes')).toBe(18);
    expect(L.scoreCategory([2, 3, 4, 5, 6], 'ones')).toBe(0);
  });
  it('H2 three and four of a kind sum all dice when they qualify', () => {
    expect(L.scoreCategory([3, 3, 3, 4, 5], 'threeOfAKind')).toBe(18);
    expect(L.scoreCategory([3, 3, 2, 4, 5], 'threeOfAKind')).toBe(0);
    expect(L.scoreCategory([2, 2, 2, 2, 6], 'fourOfAKind')).toBe(14);
    expect(L.scoreCategory([2, 2, 2, 5, 6], 'fourOfAKind')).toBe(0);
    expect(L.scoreCategory([4, 4, 4, 4, 4], 'threeOfAKind')).toBe(20);
  });
  it('H3 a full house is three of one and two of another, not five of a kind', () => {
    expect(L.scoreCategory([2, 3, 2, 3, 2], 'fullHouse')).toBe(25);
    expect(L.scoreCategory([2, 2, 2, 2, 3], 'fullHouse')).toBe(0);
    expect(L.scoreCategory([5, 5, 5, 5, 5], 'fullHouse')).toBe(0);
  });
  it('H4 small and large straights', () => {
    expect(L.scoreCategory([1, 2, 3, 4, 6], 'smallStraight')).toBe(30);
    expect(L.scoreCategory([3, 4, 5, 6, 6], 'smallStraight')).toBe(30);
    expect(L.scoreCategory([1, 2, 3, 5, 6], 'smallStraight')).toBe(0);
    expect(L.scoreCategory([2, 3, 4, 5, 6], 'largeStraight')).toBe(40);
    expect(L.scoreCategory([5, 4, 3, 2, 1], 'smallStraight')).toBe(30);
    expect(L.scoreCategory([1, 2, 3, 4, 6], 'largeStraight')).toBe(0);
  });
  it('H5 yahtzee and chance', () => {
    expect(L.scoreCategory([6, 6, 6, 6, 6], 'yahtzee')).toBe(50);
    expect(L.scoreCategory([6, 6, 6, 6, 5], 'yahtzee')).toBe(0);
    expect(L.scoreCategory([1, 2, 3, 4, 6], 'chance')).toBe(16);
  });
  it('H6 bestCategory picks the highest score with ties to the first listed, and the upper bonus', () => {
    expect(L.bestCategory([6, 6, 6, 6, 6], ['sixes', 'yahtzee', 'chance'])).toBe('yahtzee');
    expect(L.bestCategory([1, 2, 3, 4, 5], ['chance', 'largeStraight'])).toBe('largeStraight');
    expect(L.bestCategory([1, 1, 2, 2, 3], ['twos', 'ones', 'fives'])).toBe('twos');
    expect(L.bestCategory([2, 2, 3, 3, 5], ['ones', 'fours'])).toBe('ones');
    expect(L.upperBonus(63)).toBe(35);
    expect(L.upperBonus(62)).toBe(0);
  });
});
