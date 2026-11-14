import { BOARD_WIDTH, clearFullRows, collides, createBoard, mergePiece, type Board } from './board';
import { PIECES, PIECE_KINDS, cellsFor, type PieceKind, type Point } from './pieces';
import { levelForRows, scoreForLines } from './scoring';

export type Status = 'playing' | 'paused' | 'over';
export type Random = () => number;

export interface ActivePiece { kind: PieceKind; rotation: number; x: number; y: number }

export interface GameState {
  board: Board;
  active: ActivePiece;
  next: PieceKind;
  score: number;
  rows: number;
  level: number;
  status: Status;
}

export type Action =
  | { type: 'left' }
  | { type: 'right' }
  | { type: 'rotate' }
  | { type: 'softDrop' }
  | { type: 'hardDrop' }
  | { type: 'tick' }
  | { type: 'togglePause' }
  | { type: 'restart' };

export const KICKS = [0, -1, 1, -2, 2];

export function randomKind(random: Random): PieceKind {
  return PIECE_KINDS[Math.min(PIECE_KINDS.length - 1, Math.floor(random() * PIECE_KINDS.length))];
}

export function spawnPiece(kind: PieceKind): ActivePiece {
  return { kind, rotation: 0, x: Math.floor((BOARD_WIDTH - PIECES[kind].size) / 2), y: 0 };
}

export function pieceCells(p: ActivePiece): Point[] {
  return cellsFor(p.kind, p.rotation).map((c) => ({ x: c.x + p.x, y: c.y + p.y }));
}

export function createInitialState(random: Random): GameState {
  const first = randomKind(random);
  const next = randomKind(random);
  return {
    board: createBoard(),
    active: spawnPiece(first),
    next,
    score: 0,
    rows: 0,
    level: 1,
    status: 'playing',
  };
}

function landing(state: GameState): ActivePiece {
  let p = state.active;
  while (!collides(state.board, pieceCells({ ...p, y: p.y + 1 }))) p = { ...p, y: p.y + 1 };
  return p;
}

export function ghostCells(state: GameState): Point[] {
  return pieceCells(landing(state));
}

function lock(state: GameState, piece: ActivePiece, random: Random): GameState {
  const merged = mergePiece(state.board, pieceCells(piece), piece.kind);
  const { board, cleared } = clearFullRows(merged);
  const rows = state.rows + cleared;
  const spawned = spawnPiece(state.next);
  return {
    ...state,
    board,
    score: state.score + scoreForLines(cleared),
    rows,
    level: levelForRows(rows),
    active: spawned,
    next: randomKind(random),
    status: collides(board, pieceCells(spawned)) ? 'over' : 'playing',
  };
}

function move(state: GameState, dx: number, dy: number): GameState {
  const moved = { ...state.active, x: state.active.x + dx, y: state.active.y + dy };
  if (collides(state.board, pieceCells(moved))) return state;
  return { ...state, active: moved };
}

function rotate(state: GameState): GameState {
  const rotation = (state.active.rotation + 1) % 4;
  for (const dx of KICKS) {
    const cand = { ...state.active, rotation, x: state.active.x + dx };
    if (!collides(state.board, pieceCells(cand))) return { ...state, active: cand };
  }
  return state;
}

export function createReducer(random: Random) {
  return function reducer(state: GameState, action: Action): GameState {
    if (action.type === 'restart') return createInitialState(random);
    if (action.type === 'togglePause') {
      if (state.status === 'over') return state;
      return { ...state, status: state.status === 'paused' ? 'playing' : 'paused' };
    }
    if (state.status !== 'playing') return state;
    switch (action.type) {
      case 'left': return move(state, -1, 0);
      case 'right': return move(state, 1, 0);
      case 'rotate': return rotate(state);
      case 'softDrop': return move(state, 0, 1);
      case 'hardDrop': return lock(state, landing(state), random);
      case 'tick': {
        const down = move(state, 0, 1);
        return down === state ? lock(state, state.active, random) : down;
      }
    }
  };
}
