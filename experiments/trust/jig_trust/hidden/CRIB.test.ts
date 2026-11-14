import { describe, expect, it } from 'vitest';
import * as L from '../logic';

const c = (s: string) => s.split(' ');

describe('CRIB', () => {
  it('H1 fifteens count every combination that adds up to 15', () => {
    expect(L.fifteens(c('5h 5d 5s Jc 5c'))).toBe(16);
    expect(L.fifteens(c('4h 5h 6h 6d Ts'))).toBe(6);
    expect(L.fifteens(c('2h 4d 6s 8c Kh'))).toBe(0);
    expect(L.fifteens(c('Ah 4d Ks 2c 3h'))).toBe(4);
  });
  it('H2 pairs, three and four of a kind', () => {
    expect(L.pairs(c('7h 7d 2s 9c Kh'))).toBe(2);
    expect(L.pairs(c('7h 7d 7s 9c Kh'))).toBe(6);
    expect(L.pairs(c('7h 7d 9s 9c Kh'))).toBe(4);
    expect(L.pairs(c('5h 5d 5s Jc 5c'))).toBe(12);
  });
  it('H3 runs use the longest runs and count every combination', () => {
    expect(L.runs(c('3h 4d 5s 9c Kd'))).toBe(3);
    expect(L.runs(c('3h 3d 4s 5c Kd'))).toBe(6);
    expect(L.runs(c('3h 3d 4s 4c 5d'))).toBe(12);
    expect(L.runs(c('2h 3d 4s 5c 9d'))).toBe(4);
    expect(L.runs(c('Qh Kd Ac 5s 9d'))).toBe(0);
    expect(L.runs(c('9h Td Js Qc 2d'))).toBe(4);
  });
  it('H4 flush rules differ for the hand and the crib', () => {
    expect(L.flush(c('2h 5h 8h Kh'), 'Ts', false)).toBe(4);
    expect(L.flush(c('2h 5h 8h Kh'), 'Th', false)).toBe(5);
    expect(L.flush(c('2h 5h 8h Kh'), 'Ts', true)).toBe(0);
    expect(L.flush(c('2h 5h 8h Kh'), 'Th', true)).toBe(5);
    expect(L.flush(c('2h 5h 8h Ks'), 'Th', false)).toBe(0);
  });
  it('H5 nobs is the jack of the starter suit in the hand', () => {
    expect(L.nobs(c('Jh 2c 3d 4s'), '7h')).toBe(1);
    expect(L.nobs(c('Jh 2c 3d 4s'), '7d')).toBe(0);
    expect(L.nobs(c('2c 3d 4s 9h'), 'Jh')).toBe(0);
  });
  it('H6 the total, including the best possible hand of 29', () => {
    expect(L.score(c('5h 5d 5s Jc'), '5c')).toBe(29);
    expect(L.score(c('4h 5h 6h 6d'), 'Ts')).toBe(14);
    expect(L.score(c('2h 4d 6s 8c'), 'Kh')).toBe(0);
  });
});
