import { describe, expect, it } from 'vitest';
import * as L from '../logic';

const LEVEL = ['#######', '#.  $@#', '#######'];

describe('SOKO', () => {
  it('H1 parse reads walls, goals, boxes and the player, and render round-trips', () => {
    const s = L.parse(LEVEL);
    expect(s.player).toEqual({ row: 1, col: 5 });
    expect(s.walls[0][0]).toBe(true);
    expect(s.walls[1][2]).toBe(false);
    expect(s.goals[1][1]).toBe(true);
    expect(s.boxes[1][4]).toBe(true);
    expect(s.moves).toBe(0);
    expect(L.render(s)).toEqual(LEVEL);
    const other = ['#####', '#+*$#', '#####'];
    expect(L.render(L.parse(other))).toEqual(other);
  });
  it('H2 walking into floor moves the player and counts the move', () => {
    const s = L.parse(['#####', '#@  #', '#####']);
    const t = L.move(s, 'right');
    expect(t.player).toEqual({ row: 1, col: 2 });
    expect(t.moves).toBe(1);
    expect(s.player).toEqual({ row: 1, col: 1 });
  });
  it('H3 walking into a wall returns the same state object', () => {
    const s = L.parse(['#####', '#@  #', '#####']);
    expect(L.move(s, 'left')).toBe(s);
    expect(L.move(s, 'up')).toBe(s);
  });
  it('H4 pushing a box moves it one cell', () => {
    const t = L.move(L.parse(LEVEL), 'left');
    expect(L.render(t)).toEqual(['#######', '#. $@ #', '#######']);
    expect(t.moves).toBe(1);
  });
  it('H5 a box cannot be pushed into a wall or into another box', () => {
    const wall = L.parse(['#####', '# @$#', '#####']);
    expect(L.move(wall, 'right')).toBe(wall);
    const two = L.parse(['######', '#@$$ #', '######']);
    expect(L.move(two, 'right')).toBe(two);
  });
  it('H6 pushing every box onto a goal solves the level', () => {
    const s = L.parse(LEVEL);
    expect(L.isSolved(s)).toBe(false);
    const t = L.move(L.move(L.move(s, 'left'), 'left'), 'left');
    expect(L.render(t)).toEqual(['#######', '#*@   #', '#######']);
    expect(L.isSolved(t)).toBe(true);
    expect(t.moves).toBe(3);
  });
});
