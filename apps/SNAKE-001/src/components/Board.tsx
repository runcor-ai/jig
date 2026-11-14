import type { GameState } from '../game/logic'

export default function Board({ state }: { state: GameState }) {
  const n = state.gridSize
  const cells = []
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      const i = state.snake.findIndex((p) => p.x === x && p.y === y)
      let kind = 'empty'
      if (i === 0) kind = 'head'
      else if (i > 0) kind = 'body'
      else if (state.food && state.food.x === x && state.food.y === y) kind = 'food'
      cells.push(<div key={`${x},${y}`} className={`cell ${kind}`} data-cell={kind} data-x={x} data-y={y} />)
    }
  }
  return (
    <div className="board" data-testid="board" style={{ gridTemplateColumns: `repeat(${n}, 1fr)` }}>
      {cells}
    </div>
  )
}
