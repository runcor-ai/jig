import type { GameState } from '../game/types'

export default function Board({ state }: { state: GameState }) {
  const n = state.gridSize
  const cells = []
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      const idx = state.snake.findIndex((p) => p.x === x && p.y === y)
      let cls = 'cell'
      let id = 'cell'
      if (idx === 0) {
        cls += ' snake snake-head'
        id = 'snake-head'
      } else if (idx > 0) {
        cls += ' snake'
        id = 'snake'
      } else if (state.food && state.food.x === x && state.food.y === y) {
        cls += ' food'
        id = 'food'
      }
      cells.push(<div key={`${x},${y}`} className={cls} data-testid={id} />)
    }
  }
  return (
    <div
      className="board"
      data-testid="board"
      style={{ gridTemplateColumns: `repeat(${n}, 1fr)` }}
    >
      {cells}
    </div>
  )
}
