import { BALL_SIZE, HEIGHT, LEFT_PADDLE_X, PADDLE_H, PADDLE_W, RIGHT_PADDLE_X, WIDTH } from '../game/config';
import type { GameState } from '../game/logic';

const abs = (x: number, y: number, w: number, h: number): React.CSSProperties => ({
  position: 'absolute',
  left: 0,
  top: 0,
  width: w,
  height: h,
  transform: `translate(${x}px, ${y}px)`,
  background: '#fff',
});

export function Playfield({ state }: { state: GameState }) {
  return (
    <div
      data-testid="playfield"
      style={{ position: 'relative', width: WIDTH, height: HEIGHT, background: '#111', overflow: 'hidden' }}
    >
      <div
        data-testid="centre-line"
        style={{
          position: 'absolute',
          left: WIDTH / 2 - 1,
          top: 0,
          width: 2,
          height: HEIGHT,
          backgroundImage: 'linear-gradient(#555 50%, transparent 50%)',
          backgroundSize: '2px 20px',
        }}
      />
      <div style={{ position: 'absolute', top: 10, left: 0, width: WIDTH, display: 'flex', justifyContent: 'space-around', color: '#fff', fontSize: 32, fontFamily: 'monospace' }}>
        <span data-testid="score-player">{state.playerScore}</span>
        <span data-testid="score-computer">{state.computerScore}</span>
      </div>
      <div data-testid="paddle-left" style={abs(LEFT_PADDLE_X, state.leftY, PADDLE_W, PADDLE_H)} />
      <div data-testid="paddle-right" style={abs(RIGHT_PADDLE_X, state.rightY, PADDLE_W, PADDLE_H)} />
      <div data-testid="ball" style={abs(state.ball.x, state.ball.y, BALL_SIZE, BALL_SIZE)} />
      {state.status === 'gameover' && (
        <div
          style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.6)', color: '#fff', fontSize: 48, fontFamily: 'sans-serif' }}
        >
          <span data-testid="winner">{state.winner === 'player' ? 'You win!' : 'Computer wins!'}</span>
        </div>
      )}
    </div>
  );
}
