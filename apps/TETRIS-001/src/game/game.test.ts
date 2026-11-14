import { describe, expect, it } from 'vitest';
import { BOARD_WIDTH, createBoard } from './board';
import {
  createInitialState,
  createReducer,
  ghostCells,
  pieceCells,
  randomKind,
  type Action,
  type GameState,
} from './game';
import { PIECE_KINDS, type PieceKind } from './pieces';

/** Deterministic RNG cycling through the given kinds. */
function seq(kinds: PieceKind[]) {
  let i = 0;
  return () => (PIECE_KINDS.indexOf(kinds[i++ % kinds.length]) + 0.5) / PIECE_KINDS.length;
}

const BAR_RNG = () => 0.5 / 7;

function setup(rng = BAR_RNG, over: Partial<GameState> = {}) {
  const reducer = createReducer(rng);
  const state = { ...createInitialState(rng), ...over };
  return { reducer, state };
}
const run = (r: (s: GameState, a: Action) => GameState, s: GameState, ...types: Action['type'][]) =>
  types.reduce((st, type) => r(st, { type } as Action), s);

describe('R-02 spawning', () => {
  it('follows a stubbed RNG sequence and hands off next', () => {
    const rng = seq(['tee', 'block', 'bar', 'stepS']);
    const reducer = createReducer(rng);
    const s0 = createInitialState(rng);
    expect(s0.active.kind).toBe('tee');
    expect(s0.next).toBe('block');
    const s1 = reducer(s0, { type: 'hardDrop' });
    expect(s1.active.kind).toBe('block');
    expect(s1.next).toBe('bar');
    const s2 = reducer(s1, { type: 'hardDrop' });
    expect(s2.active.kind).toBe('bar');
    expect(s2.next).toBe('stepS');
  });

  it('default generator produces all 7 kinds', () => {
    const seen = new Set<PieceKind>();
    for (let i = 0; i < 1000; i++) seen.add(randomKind(Math.random));
    expect(seen.size).toBe(7);
  });

  it('spawns in rows 0-1, inside the board, centred', () => {
    for (const k of PIECE_KINDS) {
      const s = createInitialState(seq([k]));
      const cells = pieceCells(s.active);
      expect(cells.every((c) => c.y >= 0 && c.y <= 1)).toBe(true);
      expect(cells.every((c) => c.x >= 0 && c.x < BOARD_WIDTH)).toBe(true);
      const minX = Math.min(...cells.map((c) => c.x));
      const maxX = Math.max(...cells.map((c) => c.x));
      expect(Math.abs(minX + maxX - (BOARD_WIDTH - 1))).toBeLessThanOrEqual(1);
    }
  });
});

describe('R-03 movement and rotation', () => {
  it('wall rejects left/right', () => {
    const { reducer, state } = setup();
    let s = state;
    for (let i = 0; i < 10; i++) s = reducer(s, { type: 'left' });
    expect(Math.min(...pieceCells(s.active).map((c) => c.x))).toBe(0);
    expect(reducer(s, { type: 'left' })).toBe(s);
    for (let i = 0; i < 20; i++) s = reducer(s, { type: 'right' });
    expect(Math.max(...pieceCells(s.active).map((c) => c.x))).toBe(9);
    expect(reducer(s, { type: 'right' })).toBe(s);
  });

  it('rejects moving into a locked cell', () => {
    const { reducer, state } = setup();
    const board = createBoard();
    const left = Math.min(...pieceCells(state.active).map((c) => c.x));
    board[1][left - 1] = 'tee';
    const s = { ...state, board };
    expect(reducer(s, { type: 'left' })).toBe(s);
  });

  it('four rotations return to the original cells', () => {
    for (const k of PIECE_KINDS) {
      const { reducer, state } = setup(seq([k]));
      const s = { ...state, active: { ...state.active, y: 5 } };
      const after = run(reducer, s, 'rotate', 'rotate', 'rotate', 'rotate');
      expect(pieceCells(after.active)).toEqual(pieceCells(s.active));
    }
  });

  it('kicks off a wall when space allows', () => {
    const { reducer, state } = setup();
    const s = { ...state, active: { kind: 'bar' as const, rotation: 1, x: -2, y: 5 } };
    const r = reducer(s, { type: 'rotate' });
    expect(r).not.toBe(s);
    expect(r.active.rotation).toBe(2);
    expect(pieceCells(r.active).every((c) => c.x >= 0 && c.x < 10)).toBe(true);
  });

  it('rejects rotation when no kick fits', () => {
    const { reducer, state } = setup();
    const board = createBoard();
    for (let c = 0; c < 10; c++) if (c !== 5) board[7][c] = 'tee';
    const s = { ...state, board, active: { kind: 'bar' as const, rotation: 1, x: 3, y: 5 } };
    expect(reducer(s, { type: 'rotate' })).toBe(s);
  });

  it('rotation never overlaps locked cells', () => {
    const { reducer, state } = setup(seq(['tee']));
    const board = createBoard();
    board[6][3] = 'bar';
    board[8][5] = 'bar';
    let s: GameState = { ...state, board, active: { kind: 'tee', rotation: 0, x: 3, y: 5 } };
    for (let i = 0; i < 8; i++) {
      s = reducer(s, { type: 'rotate' });
      expect(pieceCells(s.active).every((c) => s.board[c.y][c.x] === null)).toBe(true);
    }
  });
});

describe('R-04 gravity and drops', () => {
  it('tick moves down; soft drop moves down without locking', () => {
    const { reducer, state } = setup();
    expect(reducer(state, { type: 'tick' }).active.y).toBe(1);
    expect(reducer(state, { type: 'softDrop' }).active.y).toBe(1);
  });

  it('soft drop at the floor does not lock', () => {
    const { reducer, state } = setup();
    const s = { ...state, active: { ...state.active, y: 18 } };
    expect(reducer(s, { type: 'softDrop' })).toBe(s);
    expect(s.board.flat().every((c) => c === null)).toBe(true);
  });

  it('hard drop lands, locks and spawns next', () => {
    const rng = seq(['block', 'tee', 'bar']);
    const { reducer, state } = setup(rng);
    const r = reducer(state, { type: 'hardDrop' });
    expect(r.board[19][4]).toBe('block');
    expect(r.board[18][5]).toBe('block');
    expect(r.active.kind).toBe('tee');
    expect(r.active.y).toBe(0);
    expect(r.next).toBe('bar');
  });

  it('tick locks a piece that cannot move down', () => {
    const { reducer, state } = setup();
    const s = { ...state, active: { ...state.active, y: 18 } };
    const r = reducer(s, { type: 'tick' });
    expect(r.board[19].filter((c) => c === 'bar')).toHaveLength(4);
    expect(r.active.y).toBe(0);
  });
});

describe('R-06 scoring through the reducer', () => {
  it('clearing 2 rows adds 300 and 2 rows; level 1 -> 2 when 9 -> 11', () => {
    const board = createBoard();
    for (const y of [18, 19]) for (let c = 2; c < 10; c++) board[y][c] = 'tee';
    const { reducer, state } = setup(seq(['block']), { board, rows: 9 });
    const s = { ...state, active: { kind: 'block' as const, rotation: 0, x: 0, y: 0 } };
    const r = reducer(s, { type: 'hardDrop' });
    expect(r.score).toBe(300);
    expect(r.rows).toBe(11);
    expect(r.level).toBe(2);
    expect(s.level).toBe(1);
    expect(r.board.flat().filter((c) => c !== null)).toHaveLength(0);
  });
});

describe('R-08 game over and restart', () => {
  function blocked() {
    const board = createBoard();
    for (const y of [0, 1]) for (let c = 0; c < 9; c++) board[y][c] = 'tee';
    const { reducer, state } = setup(BAR_RNG, { board, score: 42 });
    return { reducer, over: reducer(state, { type: 'hardDrop' }) };
  }

  it('blocked spawn sets over; later actions ignored', () => {
    const { reducer, over } = blocked();
    expect(over.status).toBe('over');
    for (const t of ['left', 'right', 'rotate', 'softDrop', 'hardDrop', 'tick', 'togglePause'] as const) {
      expect(reducer(over, { type: t })).toBe(over);
    }
  });

  it('restart resets everything', () => {
    const { reducer, over } = blocked();
    const r = reducer(over, { type: 'restart' });
    expect(r.board.flat().every((c) => c === null)).toBe(true);
    expect([r.score, r.level, r.rows, r.status]).toEqual([0, 1, 0, 'playing']);
  });
});

describe('R-09 pause', () => {
  it('toggles and ignores input while paused', () => {
    const { reducer, state } = setup();
    const p = reducer(state, { type: 'togglePause' });
    expect(p.status).toBe('paused');
    for (const t of ['left', 'right', 'rotate', 'softDrop', 'hardDrop', 'tick'] as const) {
      expect(reducer(p, { type: t })).toBe(p);
    }
    expect(reducer(p, { type: 'togglePause' }).status).toBe('playing');
  });
});

describe('R-12 ghost', () => {
  it('returns landing cells', () => {
    const { state } = setup();
    const g = ghostCells(state);
    expect(g).toHaveLength(4);
    expect(g.every((c) => c.y === 19)).toBe(true);
  });
});
