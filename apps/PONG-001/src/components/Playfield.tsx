import { useEffect, useRef } from 'react';
import { AI_X, BALL_SIZE, FIELD_H, FIELD_W, PADDLE_H, PADDLE_W, PLAYER_X, type GameState } from '../game/config';

export function Playfield({ state }: { state: GameState }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const ctx = ref.current?.getContext('2d');
    if (!ctx) return;
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, FIELD_W, FIELD_H);
    ctx.fillStyle = '#fff';
    for (let y = 0; y < FIELD_H; y += 24) ctx.fillRect(FIELD_W / 2 - 2, y, 4, 12);
    ctx.fillRect(PLAYER_X, state.playerY, PADDLE_W, PADDLE_H);
    ctx.fillRect(AI_X, state.aiY, PADDLE_W, PADDLE_H);
    ctx.fillRect(state.ball.x, state.ball.y, BALL_SIZE, BALL_SIZE);
  }, [state]);
  return (
    <canvas ref={ref} width={FIELD_W} height={FIELD_H} data-testid="playfield"
      aria-label="Pong playfield: left paddle player, right paddle computer" />
  );
}
