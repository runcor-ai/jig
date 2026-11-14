import { useGame } from './hooks/useGame';
import type { GameState, Random } from './game/game';
import { Board } from './ui/Board';
import { SidePanel } from './ui/SidePanel';

export default function App({ random, initialState }: { random?: Random; initialState?: GameState }) {
  const { state, dispatch } = useGame(random, initialState);
  return (
    <main className="app">
      <h1>Falling Blocks</h1>
      <div className="layout">
        <Board state={state} dispatch={dispatch} />
        <SidePanel state={state} />
      </div>
    </main>
  );
}
