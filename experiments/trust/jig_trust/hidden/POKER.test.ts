import { describe, expect, it } from 'vitest';
import * as L from '../logic';

const h = (s: string) => s.split(' ');

describe('POKER', () => {
  it('H1 the lower categories', () => {
    expect(L.evaluate(h('2c 7d 9h Js Ks')).category).toBe('high card');
    expect(L.evaluate(h('8c 8d 2h 5s Ks')).category).toBe('pair');
    expect(L.evaluate(h('8c 8d 2h 2s Ks')).category).toBe('two pair');
    expect(L.evaluate(h('8c 8d 8h 2s Ks')).category).toBe('three of a kind');
  });
  it('H2 the higher categories, including the A-2-3-4-5 straight', () => {
    expect(L.evaluate(h('5c 6d 7h 8s 9s'))).toEqual({ category: 'straight', ranks: [9] });
    expect(L.evaluate(h('Ac 2d 3h 4s 5s'))).toEqual({ category: 'straight', ranks: [5] });
    expect(L.evaluate(h('2h 7h 9h Jh Kh')).category).toBe('flush');
    expect(L.evaluate(h('Qc Qd Qh 4s 4c'))).toEqual({ category: 'full house', ranks: [12, 4] });
    expect(L.evaluate(h('9c 9d 9h 9s 2c'))).toEqual({ category: 'four of a kind', ranks: [9, 2] });
    expect(L.evaluate(h('Th Jh Qh Kh Ah'))).toEqual({ category: 'straight flush', ranks: [14] });
  });
  it('H3 tie-break ranks for pairs, two pair, three of a kind and high card', () => {
    expect(L.evaluate(h('Kh Kd 4s 4c 9h')).ranks).toEqual([13, 4, 9]);
    expect(L.evaluate(h('8c 8d 2h 5s Ks')).ranks).toEqual([8, 13, 5, 2]);
    expect(L.evaluate(h('8c 8d 8h 2s Ks')).ranks).toEqual([8, 13, 2]);
    expect(L.evaluate(h('2c 7d 9h Js Ks')).ranks).toEqual([13, 11, 9, 7, 2]);
  });
  it('H4 a higher category always wins, and the wheel is the lowest straight', () => {
    expect(L.compare(h('2h 7h 9h Jh Kh'), h('5c 6d 7h 8s 9s'))).toBe(1);
    expect(L.compare(h('2c 2d 3h 3s 3c'), h('Ah Kh Qh Jh 9h'))).toBe(1);
    expect(L.compare(h('Ac 2d 3h 4s 5s'), h('2c 3d 4h 5s 6s'))).toBe(-1);
    expect(L.compare(h('Ac 2d 3h 4s 5s'), h('Kc Kd Ah Qs Js'))).toBe(1);
  });
  it('H5 kickers decide within a category, and suits never do', () => {
    expect(L.compare(h('8c 8d Ah 5s 3s'), h('8h 8s Kh Qd Jc'))).toBe(1);
    expect(L.compare(h('Kh Kd 4s 4c 9h'), h('Ks Kc 4h 4d Th'))).toBe(-1);
    expect(L.compare(h('2c 7d 9h Js Ks'), h('2d 7h 9s Jc Kd'))).toBe(0);
  });
  it('H6 best returns every winning index', () => {
    expect(L.best([h('2c 7d 9h Js Ks'), h('8c 8d 2h 5s Ks'), h('3c 3d 2s 5h 9c')])).toEqual([1]);
    expect(L.best([h('2c 7d 9h Js Ks'), h('2d 7h 9s Jc Kd'), h('2h 3d 9c Jd Kh')])).toEqual([0, 1]);
  });
});
