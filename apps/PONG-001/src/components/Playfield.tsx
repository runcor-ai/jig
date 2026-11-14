import type { CSSProperties, ReactNode } from 'react';
import {
  BALL_SIZE,
  FIELD_HEIGHT,
  FIELD_WIDTH,
  LEFT_PADDLE_X,
  PADDLE_HEIGHT,
  PADDLE_WIDTH,
  RIGHT_PADDLE_X,
} from '../game/constants';
import type { GameState } from '../game/types';

const box = (x: number, y: number, w: number, h: number): CSSProperties => ({
  position: 'absolute',
  left: 0,
  top: 0,
  width: w,
  height: h,
  background: '#fff',
  transform: `translate(${x}px, ${y}px)`,
});

export function Playfield({ state, children }: { state: GameState; children?: ReactNode }) {
  return (
    <div
      data-testid="playfield"
      style={{
        position: 'relative',
        width: FIELD_WIDTH,
        height: FIELD_HEIGHT,
        background: '#111',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          position: 'absolute',
          left: FIELD_WIDTH / 2 - 1,
          top: 0,
          height: '100%',
          borderLeft: '2px dashed #666',
        }}
      />
      <div
        data-testid="left-paddle"
        data-x={LEFT_PADDLE_X}
        data-y={state.player.y}
        style={box(LEFT_PADDLE_X, state.player.y, PADDLE_WIDTH, PADDLE_HEIGHT)}
      />
      <div
        data-testid="right-paddle"
        data-x={RIGHT_PADDLE_X}
        data-y={state.ai.y}
        style={box(RIGHT_PADDLE_X, state.ai.y, PADDLE_WIDTH, PADDLE_HEIGHT)}
      />
      <div
        data-testid="ball"
        data-x={state.ball.x}
        data-y={state.ball.y}
        style={box(state.ball.x, state.ball.y, BALL_SIZE, BALL_SIZE)}
      />
      {children}
    </div>
  );
}
