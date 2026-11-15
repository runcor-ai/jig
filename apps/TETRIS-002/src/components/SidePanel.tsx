import type { GameState } from '../game/game';
import { matrixOf } from '../game/pieces';

export default function SidePanel({ state }: { state: GameState }) {
  const m = matrixOf(state.next, 0);
  return (
    <aside className="side">
      <div className="stat">
        <span className="label">Next</span>
        <div className="preview" data-testid="next" data-kind={state.next}>
          {m.map((row, r) => (
            <div className="prow" key={r}>
              {row.map((v, c) => (
                <div
                  key={c}
                  className={`cell ${v ? `locked k-${state.next}` : 'empty'}`}
                  data-filled={v ? 'true' : 'false'}
                />
              ))}
            </div>
          ))}
        </div>
      </div>
      <div className="stat">
        <span className="label">Score</span>
        <span className="value" data-testid="score">{state.score}</span>
      </div>
      <div className="stat">
        <span className="label">Level</span>
        <span className="value" data-testid="level">{state.level}</span>
      </div>
      <div className="stat">
        <span className="label">Rows</span>
        <span className="value" data-testid="rows">{state.rows}</span>
      </div>
    </aside>
  );
}
