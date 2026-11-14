import type { Dispatch } from 'react';
import { BOARD_HEIGHT, BOARD_WIDTH } from '../game/board';
import { ghostCells, pieceCells, type Action, type GameState } from '../game/game';
import { PIECES } from '../game/pieces';

export function Board({ state, dispatch }: { state: GameState; dispatch: Dispatch<Action> }) {
  const active = new Set(pieceCells(state.active).map((c) => `${c.x},${c.y}`));
  const ghost = new Set(state.status === 'over' ? [] : ghostCells(state).map((c) => `${c.x},${c.y}`));
  const cells = [];
  for (let y = 0; y < BOARD_HEIGHT; y++) {
    for (let x = 0; x < BOARD_WIDTH; x++) {
      const key = `${x},${y}`;
      const locked = state.board[y][x];
      const isActive = active.has(key);
      const kind = isActive ? state.active.kind : locked;
      const isGhost = !isActive && !locked && ghost.has(key);
      cells.push(
        <div
          key={key}
          className={`cell${kind ? ' filled' : ''}${isGhost ? ' ghost' : ''}`}
          data-testid="cell"
          data-row={y}
          data-col={x}
          data-filled={kind ? 'true' : 'false'}
          data-active={isActive ? 'true' : 'false'}
          data-ghost={isGhost ? 'true' : 'false'}
          style={kind ? { background: PIECES[kind].color } : undefined}
        />,
      );
    }
  }
  return (
    <div className="board-wrap">
      <div className="board" data-testid="board">{cells}</div>
      {state.status === 'paused' && <div className="overlay"><h2>Paused</h2></div>}
      {state.status === 'over' && (
        <div className="overlay" role="dialog" aria-label="Game over">
          <h2>Game Over</h2>
          <p>Final score: {state.score}</p>
          <button onClick={() => dispatch({ type: 'restart' })}>Restart</button>
        </div>
      )}
    </div>
  );
}
