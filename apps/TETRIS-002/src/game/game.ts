import { clearLines, collides, createBoard, dropDistance, merge } from './board';
import type { Board } from './board';
import { randomPiece, rotatePiece, spawnPiece } from './pieces';
import type { Piece, PieceKind } from './pieces';
import { levelForRows, scoreForLines } from './scoring';

export type Status = 'playing' | 'paused' | 'over';
export type Action =
  | 'left'
  | 'right'
  | 'rotate'
  | 'softDrop'
  | 'hardDrop'
  | 'tick'
  | 'togglePause'
  | 'restart';

export interface GameState {
  board: Board;
  active: Piece;
  next: PieceKind;
  score: number;
  level: number;
  rows: number;
  status: Status;
}

export function newGame(rng: () => number): GameState {
  const first = randomPiece(rng);
  const next = randomPiece(rng);
  return {
    board: createBoard(),
    active: spawnPiece(first),
    next,
    score: 0,
    level: 1,
    rows: 0,
    status: 'playing',
  };
}

function lockAndSpawn(state: GameState, piece: Piece, rng: () => number): GameState {
  const merged = merge(state.board, piece);
  const { board, cleared } = clearLines(merged);
  const rows = state.rows + cleared;
  const active = spawnPiece(state.next);
  return {
    board,
    active,
    next: randomPiece(rng),
    score: state.score + scoreForLines(cleared),
    rows,
    level: levelForRows(rows),
    status: collides(board, active) ? 'over' : 'playing',
  };
}

function tryMove(state: GameState, dx: number, dy: number): GameState {
  const moved = { ...state.active, x: state.active.x + dx, y: state.active.y + dy };
  return collides(state.board, moved) ? state : { ...state, active: moved };
}

function tryRotate(state: GameState): GameState {
  const rotated = rotatePiece(state.active);
  const kicks = state.active.kind === 'I' ? [0, -1, 1, -2, 2] : [0, -1, 1];
  for (const k of kicks) {
    const cand = { ...rotated, x: rotated.x + k };
    if (!collides(state.board, cand)) return { ...state, active: cand };
  }
  return state;
}

export function reduce(state: GameState, action: Action, rng: () => number): GameState {
  if (action === 'restart') return newGame(rng);
  if (state.status === 'over') return state;
  if (action === 'togglePause') {
    return { ...state, status: state.status === 'playing' ? 'paused' : 'playing' };
  }
  if (state.status !== 'playing') return state;

  switch (action) {
    case 'left':
      return tryMove(state, -1, 0);
    case 'right':
      return tryMove(state, 1, 0);
    case 'rotate':
      return tryRotate(state);
    case 'softDrop':
      return tryMove(state, 0, 1);
    case 'tick': {
      const moved = tryMove(state, 0, 1);
      return moved !== state ? moved : lockAndSpawn(state, state.active, rng);
    }
    case 'hardDrop': {
      const d = dropDistance(state.board, state.active);
      return lockAndSpawn(state, { ...state.active, y: state.active.y + d }, rng);
    }
    default:
      return state;
  }
}
