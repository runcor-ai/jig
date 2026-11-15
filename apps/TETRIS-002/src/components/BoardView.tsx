import { dropDistance } from '../game/board';
import type { GameState } from '../game/game';
import { COLS, ROWS, pieceCells } from '../game/pieces';

export default function BoardView({ state, showGhost = true }: { state: GameState; showGhost?: boolean }) {
  const kinds: (string | null)[][] = state.board.map((r) => r.slice());
  const mode: string[][] = state.board.map((r) => r.map((c) => (c ? 'locked' : 'empty')));

  if (showGhost && state.status !== 'over') {
    const d = dropDistance(state.board, state.active);
    for (const [x, y] of pieceCells({ ...state.active, y: state.active.y + d })) {
      if (y >= 0 && y < ROWS && x >= 0 && x < COLS) {
        kinds[y][x] = state.active.kind;
        mode[y][x] = 'ghost';
      }
    }
  }
  if (state.status !== 'over') {
    for (const [x, y] of pieceCells(state.active)) {
      if (y >= 0 && y < ROWS && x >= 0 && x < COLS) {
        kinds[y][x] = state.active.kind;
        mode[y][x] = 'active';
      }
    }
  }

  return (
    <div className="board" data-testid="board" role="grid" aria-label="Board">
      {kinds.map((row, r) =>
        row.map((k, c) => (
          <div
            key={`${r}-${c}`}
            className={`cell ${mode[r][c]}${k ? ` k-${k}` : ''}`}
            data-testid={`cell-${r}-${c}`}
            data-row={r}
            data-col={c}
            data-state={mode[r][c]}
            data-kind={k ?? ''}
          />
        )),
      )}
    </div>
  );
}
