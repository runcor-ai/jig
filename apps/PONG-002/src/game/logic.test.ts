import { describe, expect, it } from 'vitest'
import {
  AI_DEAD_ZONE, AI_REFRESH, AI_SPEED, BALL_RADIUS, BASE_SPEED, HEIGHT, LEFT_PADDLE_X,
  MAX_SPEED, PADDLE_H, PADDLE_W, PLAYER_SPEED, RIGHT_PADDLE_X, WIDTH,
} from './constants'
import { aiInput, aiTargetFor } from './ai'
import { initialState, restart, step, toggleSpace } from './logic'
import type { GameState, Input } from './types'

const rng = () => 0.5 // serve angle 0
const playing = (o: Partial<GameState> = {}): GameState => ({ ...initialState(), phase: 'playing', ...o })
const speedOf = (s: GameState) => Math.hypot(s.ball.vx, s.ball.vy)
const deg = (s: GameState) => (Math.atan2(s.ball.vy, Math.abs(s.ball.vx)) * 180) / Math.PI

describe('R-01 initial state', () => {
  it('has the fixed size, centred paddles and centred ball', () => {
    const s = initialState()
    expect(s.width).toBe(800)
    expect(s.height).toBe(500)
    expect(s.playerY).toBe((500 - PADDLE_H) / 2)
    expect(s.computerY).toBe((500 - PADDLE_H) / 2)
    expect(s.ball.x).toBe(400)
    expect(s.ball.y).toBe(250)
    expect(PADDLE_W).toBe(12)
    expect(PADDLE_H).toBe(80)
    expect(BALL_RADIUS).toBe(8)
    expect(LEFT_PADDLE_X).toBe(20)
    expect(RIGHT_PADDLE_X).toBe(768)
  })
})

describe('R-02 player control', () => {
  it('moves up and down at 400 units/s', () => {
    const dt = 1 / 60
    const s = playing()
    expect(step(s, -1, dt, rng).playerY).toBeCloseTo(s.playerY - 400 * dt)
    expect(step(s, 1, dt, rng).playerY).toBeCloseTo(s.playerY + PLAYER_SPEED * dt)
    expect(step(s, 0, dt, rng).playerY).toBe(s.playerY)
  })
  it('clamps inside the playfield', () => {
    expect(step(playing({ playerY: 1 }), -1, 1 / 30, rng).playerY).toBe(0)
    expect(step(playing({ playerY: HEIGHT - PADDLE_H - 1 }), 1, 1 / 30, rng).playerY).toBe(HEIGHT - PADDLE_H)
  })
})

describe('R-03 computer opponent', () => {
  it('never moves faster than 260 units/s', () => {
    for (const target of [-1000, 0, 100, 250, 400, 5000]) {
      for (const y of [0, 100, 210, 420]) {
        expect(Math.abs(aiInput(y, target))).toBeLessThanOrEqual(AI_SPEED)
      }
    }
    expect(AI_SPEED).toBeLessThan(PLAYER_SPEED)
    // and in the simulation
    const dt = 1 / 60
    const s = playing({ computerY: 0, aiTargetY: 450, ball: { x: 400, y: 450, vx: 100, vy: 0 } })
    const n = step(s, 0, dt, rng)
    expect(Math.abs(n.computerY - s.computerY)).toBeLessThanOrEqual(AI_SPEED * dt + 1e-9)
  })
  it('refreshes its target no more often than every 150 ms', () => {
    const dt = 1 / 60
    let s = playing({ ball: { x: 300, y: 100, vx: 1, vy: 0 }, computerY: 210 })
    const refreshes: number[] = []
    let prev = s.aiTargetY
    for (let i = 1; i <= 60; i++) {
      s = step(s, 0, dt, rng)
      if (s.aiTargetY !== prev) {
        refreshes.push(i * dt)
        prev = s.aiTargetY
      }
      // keep the ball changing so the target would change if it could
      s = { ...s, ball: { ...s.ball, y: s.ball.y + 3 * i } }
    }
    expect(refreshes.length).toBeGreaterThan(0)
    expect(refreshes.length).toBeLessThanOrEqual(Math.ceil(1 / AI_REFRESH))
    for (let i = 1; i < refreshes.length; i++) {
      expect(refreshes[i] - refreshes[i - 1]).toBeGreaterThanOrEqual(AI_REFRESH - 1e-6)
    }
    // does not refresh in the first few frames
    const early = step(playing({ aiTargetY: 250, ball: { x: 300, y: 50, vx: 100, vy: 0 } }), 0, dt, rng)
    expect(early.aiTargetY).toBe(250)
  })
  it('does not move inside the dead zone', () => {
    const centre = 210 + PADDLE_H / 2
    expect(aiInput(210, centre)).toBe(0)
    expect(aiInput(210, centre + AI_DEAD_ZONE)).toBe(0)
    expect(aiInput(210, centre - AI_DEAD_ZONE)).toBe(0)
    expect(aiInput(210, centre + AI_DEAD_ZONE + 1)).toBe(AI_SPEED)
    expect(aiInput(210, centre - AI_DEAD_ZONE - 1)).toBe(-AI_SPEED)
  })
  it('drifts to the centre when the ball moves away', () => {
    const away = { x: 300, y: 20, vx: -300, vy: 0 }
    expect(aiTargetFor(away)).toBe(HEIGHT / 2)
    expect(aiInput(0, aiTargetFor(away))).toBeGreaterThan(0) // from the top, toward the centre
    expect(aiInput(420, aiTargetFor(away))).toBeLessThan(0) // from the bottom
    expect(aiInput((HEIGHT - PADDLE_H) / 2, aiTargetFor(away))).toBe(0) // holds still at the centre
  })
  it('lets a steep, fast shot off the player paddle edge get past the AI', () => {
    // Player returns a fast ball with the edge of the paddle; simulate with no player input.
    let s = playing({
      playerY: 100,
      ball: { x: 40, y: 104, vx: -600, vy: 0 },
      computerY: 210,
    })
    for (let i = 0; i < 60 * 10 && s.playerScore + s.computerScore === 0; i++) {
      s = step(s, 0, 1 / 60, rng)
    }
    expect(s.playerScore).toBe(1)
    expect(s.computerScore).toBe(0)
  })
})

describe('R-04 bounces', () => {
  it('flips vy at the top and bottom walls and keeps the ball inside', () => {
    const top = step(playing({ ball: { x: 400, y: BALL_RADIUS + 1, vx: 100, vy: -300 } }), 0, 1 / 60, rng)
    expect(top.ball.vy).toBeGreaterThan(0)
    expect(top.ball.y).toBeGreaterThanOrEqual(BALL_RADIUS)
    const bot = step(playing({ ball: { x: 400, y: HEIGHT - BALL_RADIUS - 1, vx: 100, vy: 300 } }), 0, 1 / 60, rng)
    expect(bot.ball.vy).toBeLessThan(0)
    expect(bot.ball.y).toBeLessThanOrEqual(HEIGHT - BALL_RADIUS)
  })
  it('gives 0 / -60 / +60 degrees at centre / top edge / bottom edge of the player paddle', () => {
    const pY = 200
    const hit = (y: number) =>
      step(playing({ playerY: pY, ball: { x: 40, y, vx: -300, vy: 0 } }), 0, 1 / 60, rng)
    const c = hit(pY + PADDLE_H / 2)
    expect(deg(c)).toBeCloseTo(0)
    expect(deg(hit(pY))).toBeCloseTo(-60)
    expect(deg(hit(pY + PADDLE_H))).toBeCloseTo(60)
    expect(c.ball.vx).toBeGreaterThan(0) // away from the left paddle
  })
  it('multiplies speed by 1.05 and caps at 900', () => {
    const pY = 200
    const a = step(playing({ playerY: pY, ball: { x: 40, y: pY + 40, vx: -400, vy: 0 } }), 0, 1 / 60, rng)
    expect(speedOf(a)).toBeCloseTo(420)
    const b = step(playing({ playerY: pY, ball: { x: 40, y: pY + 40, vx: -880, vy: 0 } }), 0, 1 / 60, rng)
    expect(speedOf(b)).toBeCloseTo(MAX_SPEED)
  })
  it('sends the ball left after hitting the right paddle', () => {
    const cY = 200
    const s = step(
      playing({ computerY: cY, aiTargetY: cY + 40, ball: { x: 755, y: cY + 40, vx: 400, vy: 0 } }),
      0, 1 / 60, rng,
    )
    expect(s.ball.vx).toBeLessThan(0)
    expect(speedOf(s)).toBeCloseTo(420)
  })
  it('does not tunnel through a paddle at max speed with dt 1/60', () => {
    // approach the left paddle at 900 u/s (15 units per frame) from several starting offsets
    for (let x0 = 300; x0 < 316; x0 += 1) {
      let s = playing({ playerY: 200, ball: { x: x0, y: 240, vx: -MAX_SPEED, vy: 0 } })
      let bounced = false
      for (let i = 0; i < 120 && !bounced; i++) {
        s = step(s, 0, 1 / 60, rng)
        if (s.ball.vx > 0) bounced = true
        expect(s.computerScore).toBe(0)
      }
      expect(bounced).toBe(true)
    }
    // and with the clamped maximum dt (1/30)
    let s = playing({ playerY: 200, ball: { x: 100, y: 240, vx: -MAX_SPEED, vy: 0 } })
    for (let i = 0; i < 10; i++) s = step(s, 0, 1 / 30, rng)
    expect(s.computerScore).toBe(0)
    expect(s.ball.vx).toBeGreaterThan(0)
  })
})

describe('R-05 scoring and win', () => {
  it('right side scores when the ball passes x<0, and the ball resets to the centre at 300', () => {
    const s = step(playing({ playerY: 0, ball: { x: 2, y: 400, vx: -300, vy: 0 } }), 0, 1 / 30, rng)
    expect(s.computerScore).toBe(1)
    expect(s.playerScore).toBe(0)
    expect(s.ball.x).toBe(WIDTH / 2)
    expect(s.ball.y).toBe(HEIGHT / 2)
    expect(speedOf(s)).toBeCloseTo(BASE_SPEED)
    expect(s.ball.vx).toBeLessThan(0) // served toward the player who lost
    expect(s.phase).toBe('playing')
    expect(s.serveDelay).toBe(0.5)
  })
  it('left side scores when the ball passes x>width', () => {
    const s = step(playing({ computerY: 0, ball: { x: 799, y: 400, vx: 600, vy: 0 } }), 0, 1 / 30, rng)
    expect(s.playerScore).toBe(1)
    expect(s.ball.vx).toBeGreaterThan(0) // served toward the computer, who lost
    expect(speedOf(s)).toBeCloseTo(BASE_SPEED)
  })
  it('serve angle stays within +-30 degrees', () => {
    for (const r of [0, 1, 0.25]) {
      const s = step(playing({ playerY: 0, ball: { x: 2, y: 400, vx: -300, vy: 0 } }), 0, 1 / 30, () => r)
      expect(Math.abs(deg(s))).toBeLessThanOrEqual(30 + 1e-9)
    }
  })
  it('holds the ball during the 0.5 s serve delay', () => {
    let s = step(playing({ playerY: 0, ball: { x: 2, y: 400, vx: -300, vy: 0 } }), 0, 1 / 30, rng)
    const b = s.ball
    s = step(s, 0, 1 / 30, rng)
    expect(s.ball).toEqual(b)
    for (let i = 0; i < 20; i++) s = step(s, 0, 1 / 30, rng)
    expect(s.ball.x).not.toBe(b.x)
  })
  it('score 10 sets won with the winner and then freezes', () => {
    const p = step(playing({ playerScore: 9, computerY: 0, ball: { x: 799, y: 400, vx: 600, vy: 0 } }), 0, 1 / 30, rng)
    expect(p.playerScore).toBe(10)
    expect(p.phase).toBe('won')
    expect(p.winner).toBe('player')
    const c = step(playing({ computerScore: 9, playerY: 0, ball: { x: 1, y: 400, vx: -600, vy: 0 } }), 0, 1 / 30, rng)
    expect(c.phase).toBe('won')
    expect(c.winner).toBe('computer')
    const after = step(p, 1, 1 / 30, rng)
    expect(after).toEqual(p)
    expect(after.playerScore).toBe(10)
  })
})

describe('R-06 phases', () => {
  it('toggles ready -> playing -> paused -> playing and ignores won', () => {
    let s = initialState()
    expect(s.phase).toBe('ready')
    s = toggleSpace(s)
    expect(s.phase).toBe('playing')
    s = toggleSpace(s)
    expect(s.phase).toBe('paused')
    s = toggleSpace(s)
    expect(s.phase).toBe('playing')
    const won = { ...s, phase: 'won' as const, winner: 'player' as const }
    expect(toggleSpace(won).phase).toBe('won')
  })
  it('does not advance while paused or ready', () => {
    const s = { ...initialState(), phase: 'paused' as const }
    expect(step(s, 1, 1 / 60, rng)).toEqual(s)
    expect(step(initialState(), 1, 1 / 60, rng)).toEqual(initialState())
  })
  it('restart returns the initial state', () => {
    expect(restart()).toEqual(initialState())
  })
})

describe('R-09 purity', () => {
  it('does not mutate its argument and is deterministic', () => {
    const s = playing()
    const snapshot = JSON.parse(JSON.stringify(s))
    const a = step(s, 1 as Input, 1 / 60, rng)
    const b = step(s, 1 as Input, 1 / 60, rng)
    expect(s).toEqual(snapshot)
    expect(a).not.toBe(s)
    expect(a).toEqual(b)
  })
  it('clamps dt to 1/30', () => {
    const s = playing()
    expect(step(s, 1, 5, rng)).toEqual(step(s, 1, 1 / 30, rng))
  })
})
