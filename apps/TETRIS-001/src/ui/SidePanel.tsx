import { cellsFor, PIECES } from '../game/pieces';
import type { GameState } from '../game/game';

export function SidePanel({ state }: { state: GameState }) {
  const filled = new Set(cellsFor(state.next, 0).map((c) => `${c.x},${c.y}`));
  const color = PIECES[state.next].color;
  const preview = [];
  for (let y = 0; y < 4; y++) {
    for (let x = 0; x < 4; x++) {
      const on = filled.has(`${x},${y}`);
      preview.push(
        <div
          key={`${x},${y}`}
          className={`cell${on ? ' filled' : ''}`}
          data-testid="preview-cell"
          data-filled={on ? 'true' : 'false'}
          style={on ? { background: color } : undefined}
        />,
      );
    }
  }
  return (
    <aside className="side">
      <section>
        <h3>Next</h3>
        <div className="preview" data-testid="preview">{preview}</div>
      </section>
      <dl className="hud">
        <dt>Score</dt><dd data-testid="score">{state.score}</dd>
        <dt>Level</dt><dd data-testid="level">{state.level}</dd>
        <dt>Rows</dt><dd data-testid="rows">{state.rows}</dd>
      </dl>
      <section className="legend">
        <h3>Controls</h3>
        <ul>
          <li><kbd>Left</kbd>/<kbd>Right</kbd> move</li>
          <li><kbd>Up</kbd> rotate</li>
          <li><kbd>Down</kbd> soft drop</li>
          <li><kbd>Space</kbd> hard drop</li>
          <li><kbd>P</kbd> pause</li>
        </ul>
      </section>
    </aside>
  );
}
