import { describe, expect, it } from 'vitest';
import * as L from '../logic';

describe('BJACK', () => {
  it('H1 number and face cards', () => {
    expect(L.handValue(['2', '3'])).toEqual({ total: 5, soft: false });
    expect(L.handValue(['K', 'Q'])).toEqual({ total: 20, soft: false });
    expect(L.handValue(['10', 'J', '5'])).toEqual({ total: 25, soft: false });
  });
  it('H2 aces count 11 unless that busts, and soft says so', () => {
    expect(L.handValue(['A', '6'])).toEqual({ total: 17, soft: true });
    expect(L.handValue(['A', '6', '10'])).toEqual({ total: 17, soft: false });
    expect(L.handValue(['A', 'A'])).toEqual({ total: 12, soft: true });
    expect(L.handValue(['A', 'A', '9'])).toEqual({ total: 21, soft: true });
    expect(L.handValue(['A', 'A', 'A', 'K'])).toEqual({ total: 13, soft: false });
  });
  it('H3 blackjack is exactly two cards totalling 21', () => {
    expect(L.isBlackjack(['A', 'K'])).toBe(true);
    expect(L.isBlackjack(['10', 'A'])).toBe(true);
    expect(L.isBlackjack(['7', '7', '7'])).toBe(false);
    expect(L.isBlackjack(['A', '9'])).toBe(false);
  });
  it('H4 the dealer hits below 17 and on soft 17, and stands on hard 17', () => {
    expect(L.dealerShouldHit(['10', '6'])).toBe(true);
    expect(L.dealerShouldHit(['A', '6'])).toBe(true);
    expect(L.dealerShouldHit(['10', '7'])).toBe(false);
    expect(L.dealerShouldHit(['A', '6', '10'])).toBe(false);
    expect(L.dealerShouldHit(['A', '7'])).toBe(false);
  });
  it('H5 busts and blackjacks decide the outcome first', () => {
    expect(L.outcome(['K', 'Q', '5'], ['K', 'Q', '5'])).toBe('lose');
    expect(L.outcome(['A', 'K'], ['10', '9'])).toBe('blackjack');
    expect(L.outcome(['A', 'K'], ['A', 'Q'])).toBe('push');
    expect(L.outcome(['10', '5', '6'], ['A', 'Q'])).toBe('lose');
    expect(L.outcome(['10', '8'], ['10', '6', '9'])).toBe('win');
  });
  it('H6 otherwise the higher total wins and equal totals push', () => {
    expect(L.outcome(['10', '9'], ['10', '8'])).toBe('win');
    expect(L.outcome(['10', '7'], ['10', '8'])).toBe('lose');
    expect(L.outcome(['10', '8'], ['9', '9'])).toBe('push');
  });
});
